"""Actual optional JPEG stress smoke using the private browser smoke session."""
import json
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[2]

def main():
    evidence=json.loads((ROOT/'docs/screenshots/gpu-browser-qa.json').read_text())
    session=json.loads((ROOT/'data/browser-smoke/session.json').read_text())
    cookies={cookie['name']:cookie['value'] for cookie in session['cookies']}
    protection=evidence['protection']
    body=dict(protection_job_id=protection['id'],mask_id=protection['output']['scope']['mask'],prompt='a shiny silver ball on the background',editor='sd15_inpaint',seeds=[11],channel='jpeg_simulation')
    with httpx.Client(base_url='http://127.0.0.1:8000/api/v1',cookies=cookies,timeout=30) as client:
        response=client.post('/assets/'+protection['asset_id']+'/edit-tests',json=body)
        response.raise_for_status()
        job_id=response.json()['id']
        started=time.monotonic()
        while time.monotonic()-started<600:
            job=client.get('/jobs/'+job_id).json()
            print(job['state'],job['stage'],flush=True)
            if job['state'] not in ('queued','running'):
                break
            time.sleep(5)
        if job['state']!='succeeded':
            raise RuntimeError('JPEG smoke failed: '+json.dumps(job))
        experiment=client.get('/experiments/'+job['output']['experiment_id']).json()
        assert experiment['config']['channel']=='jpeg_simulation'
        pair=experiment['pairs'][0]
        assert pair['clean']!=protection['output']['artifacts']['clean']
        assert pair['protected']!=protection['output']['artifacts']['protected']
        result=dict(purpose='Synthetic JPEG stress smoke; not an Instagram round trip or efficacy benchmark',passed=True,experiment=experiment)
        (ROOT/'docs/screenshots/jpeg-channel-smoke.json').write_text(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
