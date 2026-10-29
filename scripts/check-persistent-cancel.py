"""Actual warm-runtime cancellation and fresh-process recovery check."""
import json
from pathlib import Path
import time
import httpx

root=Path(__file__).resolve().parents[1]
batch=json.loads((root/'outputs/dnew-tests/2026-10-28/results.json').read_text())
session=json.loads((root/'data/dnew-tests/session.json').read_text())
source=batch['images'][0]
body=dict(mask_id=source['protection']['output']['scope']['mask'],profile='smoke',seed=42,epsilon=2/255)
url='/assets/'+source['asset_id']+'/protect'
with httpx.Client(base_url='http://127.0.0.1:8000/api/v1',cookies=session['cookies'],timeout=30) as client:
    response=client.post(url,json=body);response.raise_for_status()
    job_id=response.json()['id']
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        job=client.get('/jobs/'+job_id).json()
        if job['state']=='running' and (job['completed_steps'] or 0)>=1:
            break
        if job['state'] not in ('queued','running'):
            raise RuntimeError('Job finished before a real iteration could be cancelled.')
        time.sleep(.15)
    else:
        raise RuntimeError('Did not reach a cancellable real GPU iteration.')
    before=time.monotonic()
    response=client.post('/jobs/'+job_id+'/cancel');response.raise_for_status()
    while time.monotonic()-before<30:
        cancelled=client.get('/jobs/'+job_id).json()
        if cancelled['state'] not in ('queued','running'):
            break
        time.sleep(.2)
    assert cancelled['state']=='cancelled' and cancelled['output'] is None
    cancellation_seconds=time.monotonic()-before
    print('Actual GPU cancellation passed.',flush=True)
    response=client.post(url,json=body);response.raise_for_status()
    recovery_id=response.json()['id']
    before_recovery=time.monotonic()
    while time.monotonic()-before_recovery<180:
        recovery=client.get('/jobs/'+recovery_id).json()
        if recovery['state'] not in ('queued','running'):
            break
        time.sleep(.5)
    assert recovery['state']=='succeeded', recovery
    result=dict(passed=True,cancelled_job_id=job_id,cancelled_at_completed_steps=job['completed_steps'],cancellation_seconds=cancellation_seconds,recovery_job_id=recovery_id,recovery_quality=recovery['output']['quality'])
    (root/'data/dnew-tests/cancellation-recovery.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
