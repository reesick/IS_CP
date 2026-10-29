import json
import time
from pathlib import Path
from uuid import uuid4
import pytest
from backend.app import db,worker
from backend.app.services import artifacts,jobs
from backend.app.settings import DATA
from PIL import Image

@pytest.fixture
def job():
    db.init()
    # Test-only synthetic data, never measured ML evidence.
    owner,asset_id=str(uuid4()),str(uuid4())
    directory=DATA/asset_id;directory.mkdir()
    clean=directory/'clean.png';mask=directory/'mask.png'
    Image.new('RGB',(512,512),(100,100,100)).save(clean)
    Image.new('L',(512,512),0).save(mask)
    clean_id=artifacts.add(owner,asset_id,clean,'clean')
    mask_id=artifacts.add(owner,asset_id,mask,'mask')
    db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?)',(asset_id,owner,'{}',None,clean_id,mask_id,time.time()))
    jid=jobs.enqueue(owner,asset_id,'protect',dict(mask_id=mask_id,epsilon=4/255))
    # Claim the specific test job to avoid depending on unrelated test queue rows.
    db.execute("UPDATE jobs SET state='running' WHERE id=?",(jid,))
    return db.one('SELECT * FROM jobs WHERE id=?',(jid,))

def fake_process(monkeypatch,result,output=False):
    class FakeProcess:
        pid=0
        def __init__(self,args,**kwargs):
            request=json.loads(Path(args[-1]).read_text())
            if output:
                Image.new('RGB',(512,512),(101,101,101)).save(request['output_path'])
            Path(request['result_path']).write_text(json.dumps(result))
        def poll(self):return 0
    monkeypatch.setattr(worker.subprocess,'Popen',FakeProcess)

def test_oom_never_succeeds(job,monkeypatch):
    fake_process(monkeypatch,dict(ok=False,error_code='cuda_oom',error_message='GPU memory exhausted'))
    worker.process_job(job)
    row=db.one('SELECT * FROM jobs WHERE id=?',(job['id'],))
    assert row['state']=='failed' and row['error_code']=='cuda_oom'
    assert row['output'] is None

def test_cancellation_does_not_publish_result(job,monkeypatch):
    fake_process(monkeypatch,dict(ok=True,output={}),output=True)
    db.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?',(job['id'],))
    worker.process_job(job)
    row=db.one('SELECT * FROM jobs WHERE id=?',(job['id'],))
    assert row['state']=='cancelled' and row['output'] is None

def test_completed_compute_retains_untested_effectiveness(job,monkeypatch):
    fake_process(monkeypatch,dict(ok=True,output=dict(test_fixture=True)),output=True)
    worker.process_job(job)
    row=db.one('SELECT * FROM jobs WHERE id=?',(job['id'],))
    output=json.loads(row['output'])
    assert row['state']=='succeeded'
    assert output['quality']['gate']=='passed'
    assert output['effectiveness']=='not_tested'

def test_failed_quality_has_diagnostic_only(job,monkeypatch):
    fake_process(monkeypatch,dict(ok=True,output=dict(test_fixture=True)),output=False)
    # Identical pixels fail the actual-change gate.
    class IdenticalProcess:
        pid=0
        def __init__(self,args,**kwargs):
            request=json.loads(Path(args[-1]).read_text())
            Image.open(request['clean_path']).save(request['output_path'])
            Path(request['result_path']).write_text(json.dumps(dict(ok=True,output={})))
        def poll(self):return 0
    monkeypatch.setattr(worker.subprocess,'Popen',IdenticalProcess)
    worker.process_job(job)
    row=db.one('SELECT * FROM jobs WHERE id=?',(job['id'],))
    output=json.loads(row['output'])
    assert row['state']=='rejected_quality'
    assert 'protected' not in output['artifacts']
    assert 'diagnostic' in output['artifacts']
