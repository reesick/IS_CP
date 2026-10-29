import json
import os
import signal
import subprocess
import time
from pathlib import Path
from uuid import uuid4
from . import db
from .settings import ROOT,DATA,ML_PYTHON,JOB_TIMEOUT,private_path,settings
from .ml_runtime import MLRuntime
from .services import artifacts,jobs
from .services.metrics import measure

_stop=False
_runtime=MLRuntime()

def stop(*_):
    global _stop
    _stop=True

def kill(process):
    if process.poll() is not None:
        return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        process.kill()
    process.wait(timeout=20)

def update(job_id,**fields):
    fields['updated']=time.time()
    with db.connect() as con:
        if fields.get('state') in ('succeeded','rejected_quality'):
            con.execute('BEGIN IMMEDIATE')
            row=con.execute('SELECT cancel_requested FROM jobs WHERE id=?',(job_id,)).fetchone()
            if not row:
                return
            if row['cancel_requested'] or _stop:
                fields.update(state='cancelled',stage='Cancelled',output=None)
        con.execute('UPDATE jobs SET '+','.join(f'{key}=?' for key in fields)+' WHERE id=?',(*fields.values(),job_id))

def process_job(job):
    try:
        return _process_job(job)
    except Exception:
        import traceback
        traceback.print_exc()
        update(job['id'],state='failed',stage='Job input unavailable',error_code='invalid_saved_input',error_message='The saved job input is missing or invalid. Re-upload the image and try again.')

def _process_job(job):
    owner,asset_id=job['owner'],job['asset_id']
    asset=db.one('SELECT * FROM assets WHERE id=? AND owner=?',(asset_id,owner))
    if not asset:
        update(job['id'],state='cancelled',stage='Image deleted')
        return
    config=json.loads(job['config'])
    config['checkpoint_unet']=settings.unet_checkpointing
    directory=private_path(f'{asset_id}/{job["id"]}')
    directory.mkdir(parents=True,exist_ok=True)
    clean=artifacts.get(asset['clean'],owner)['file']
    mask=artifacts.get(config['mask_id'],owner)['file']
    req=dict(kind=job['kind'],clean_path=str(clean),mask_path=str(mask),config=config,output_path=str(directory/'protected.png'),output_dir=str(directory),progress_path=str(directory/'progress.json'),cancel_path=str(directory/'cancel'),result_path=str(directory/'result.json'))
    if job['kind']=='edit':
        protection=db.one('SELECT output FROM jobs WHERE id=?',(config['protection_job_id'],))
        req['protected_path']=str(artifacts.get(json.loads(protection['output'])['artifacts']['protected'],owner)['file'])
    input_path=directory/'request.json'
    input_path.write_text(json.dumps(req))
    started=time.monotonic()
    process=None
    try:
        with (directory/'worker.log').open('w') as log:
            process=_runtime.submit(input_path) if settings.persistent_ml else subprocess.Popen([str(ML_PYTHON),'-m','backend.app.ml_runner',str(input_path)],cwd=ROOT,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            cancel_started=None
            while process.poll() is None and not Path(req['result_path']).exists():
                row=db.one('SELECT cancel_requested FROM jobs WHERE id=?',(job['id'],))
                cancelled=_stop or not row or row['cancel_requested']
                if cancelled:
                    PathCancel=directory/'cancel'
                    PathCancel.touch(exist_ok=True)
                    cancel_started=cancel_started or time.monotonic()
                    if time.monotonic()-cancel_started>15:
                        kill(process)
                if time.monotonic()-started>JOB_TIMEOUT:
                    kill(process)
                    update(job['id'],state='failed',stage='Timed out',error_code='job_timeout',error_message='Job exceeded the configured time limit.')
                    return
                fields=dict(heartbeat=time.time())
                progress=directory/'progress.json'
                if progress.exists():
                    try:
                        fields.update(json.loads(progress.read_text()))
                    except (ValueError,OSError):
                        pass
                update(job['id'],**fields)
                db.execute('INSERT OR REPLACE INTO worker_status VALUES(1,?,?)',(time.time(),os.getpid()))
                time.sleep(.5)
            if not settings.persistent_ml and process.poll() is None:
                process.wait(timeout=30)
            row=db.one('SELECT cancel_requested FROM jobs WHERE id=?',(job['id'],))
            if _stop or not row or row['cancel_requested']:
                if settings.persistent_ml:
                    _runtime.close()
                update(job['id'],state='cancelled',stage='Cancelled')
                return
        result_path=directory/'result.json'
        result=json.loads(result_path.read_text()) if result_path.exists() else dict(ok=False,error_code='process_interrupted',error_message='ML process exited without a result. Inspect the private job log.')
        if not result['ok']:
            if settings.persistent_ml:
                _runtime.close()
            update(job['id'],state='cancelled' if result['error_code']=='cancelled' else 'failed',stage='Model execution stopped',error_code=result['error_code'],error_message=result['error_message'])
            return
        if job['kind']=='protect':
            quality=measure(clean,directory/'protected.png',config['epsilon'])
            passed=quality['gate']=='passed'
            artifact_id=artifacts.add(owner,asset_id,directory/'protected.png','protected' if passed else 'rejected_diagnostic')
            output=dict(protection_generated=passed,effectiveness='not_tested',quality=quality,artifacts={'clean':asset['clean'],('protected' if passed else 'diagnostic'):artifact_id},provenance=result['output'],elapsed_seconds=time.monotonic()-started,scope=dict(editor='sd15_inpaint',mask=config['mask_id'],channel='local_png'))
            update(job['id'],state='succeeded' if passed else 'rejected_quality',stage='Protection generated' if passed else 'Output rejected by quality gate',output=json.dumps(output))
        else:
            raw=result['output']
            protected_id=json.loads(protection['output'])['artifacts']['protected']
            pairs=[]
            for pair in raw['pairs']:
                entry=dict(seed=pair['seed'],clean=asset['clean'],protected=protected_id,safety_filtered=pair.get('safety_filtered',False))
                for name,source in (('clean','clean_input'),('protected','protected_input')):
                    if pair.get(source):
                        input_path=private_path(str(Path(pair[source]).resolve().relative_to(DATA)))
                        entry[name]=artifacts.add(owner,asset_id,input_path,f'{name}_{config["channel"]}_input')
                for name in ('edit_clean','edit_protected'):
                    path=private_path(str(Path(pair[name]).resolve().relative_to(DATA)))
                    entry[name]=artifacts.add(owner,asset_id,path,name)
                pairs.append(entry)
            experiment_id=str(uuid4())
            metadata={k:v for k,v in raw.items() if k!='pairs'}
            db.execute('INSERT INTO experiments VALUES(?,?,?,?,?,?,?)',(experiment_id,owner,asset_id,json.dumps(config|metadata),json.dumps(pairs),None,'inconclusive'))
            update(job['id'],state='succeeded',stage='Comparison ready for human review',output=json.dumps(dict(experiment_id=experiment_id,pairs=pairs,effectiveness='inconclusive')))
    except BaseException:
        import traceback
        traceback.print_exc()
        if process:
            kill(process)
        update(job['id'],state='failed',stage='Worker error',error_code='worker_error',error_message='The worker could not complete this job. Inspect local worker logs.')
    finally:
        if settings.persistent_ml:
            _runtime.mark_idle()

def main():
    import msvcrt
    lock=(DATA/'worker.lock').open('a+b')
    lock.write(b'0'); lock.flush();lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        raise SystemExit('Another ImageShield worker is already running.')
    db.init()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    db.execute("UPDATE jobs SET state='failed',stage='Worker interrupted',error_code='interrupted',error_message='Worker restarted before completion.' WHERE state='running'")
    while not _stop:
        db.execute('INSERT OR REPLACE INTO worker_status VALUES(1,?,?)',(time.time(),os.getpid()))
        job=jobs.claim()
        if job:
            process_job(job)
        else:
            _runtime.trim_idle()
            time.sleep(1)
    _runtime.close()
    lock.close()

if __name__=='__main__':
    main()
