import json
import secrets
import time
import shutil
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from uuid import uuid4
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeTimedSerializer, BadSignature
from . import db
from .settings import ROOT, DATA, MAX_BYTES, private_path
from .schemas import ProtectRequest, EditRequest, ReviewRequest
from .services import uploads, artifacts, jobs
from .services.capabilities import capabilities

secret_path=DATA/'session.secret'
if not secret_path.exists():
    try:
        with secret_path.open('x') as f:
            f.write(secrets.token_hex(32))
    except FileExistsError:
        pass
signer=URLSafeTimedSerializer(secret_path.read_text(),salt='imageshield-session')
_rates=defaultdict(deque)

@asynccontextmanager
async def lifespan(app):
    db.init()
    yield

app=FastAPI(title='ImageShield local research API',lifespan=lifespan,docs_url='/api/docs')

def fail(status,code,message,retryable=False):
    raise HTTPException(status,detail=dict(code=code,message=message,retryable=retryable))

@app.middleware('http')
async def local_security(request,call_next):
    request.state.request_id=str(uuid4())
    host=request.url.hostname
    if host not in ('localhost','127.0.0.1','::1','testserver'):
        return JSONResponse({'error':{'code':'invalid_host','message':'Use the local loopback address.','retryable':False},'request_id':request.state.request_id},400)
    mutation=request.method not in ('GET','HEAD','OPTIONS')
    origin=request.headers.get('origin')
    if mutation and origin and origin!=str(request.base_url).rstrip('/'):
        return JSONResponse({'error':{'code':'invalid_origin','message':'Cross-origin mutations are not allowed.','retryable':False},'request_id':request.state.request_id},403)
    try:
        content_length=int(request.headers.get('content-length','0') or '0')
    except ValueError:
        content_length=MAX_BYTES+256*1024+1
    if content_length>MAX_BYTES+256*1024:
        return JSONResponse({'error':{'code':'upload_too_large','message':'Upload limit is 10 MiB.','retryable':False},'request_id':request.state.request_id},413)
    token=request.cookies.get('imageshield_session')
    try:
        owner=signer.loads(token,max_age=86400*30) if token else None
    except BadSignature:
        owner=None
    new=not owner
    request.state.owner=owner or str(uuid4())
    if mutation:
        window=_rates[request.state.owner]
        now=time.time()
        while window and window[0]<now-60:
            window.popleft()
        if len(window)>=60:
            return JSONResponse({'error':{'code':'rate_limit','message':'Too many requests. Retry in a minute.','retryable':True},'request_id':request.state.request_id},429)
        window.append(now)
    response=await call_next(request)
    if new:
        response.set_cookie('imageshield_session',signer.dumps(request.state.owner),httponly=True,samesite='strict',max_age=86400*30)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' blob: data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(HTTPException)
async def http_error(request,exc):
    detail=exc.detail if isinstance(exc.detail,dict) else dict(code='request_failed',message=str(exc.detail),retryable=False)
    return JSONResponse({'error':detail,'request_id':request.state.request_id},exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    return JSONResponse({'error':{'code':'invalid_configuration','message':'Check the submitted fields and allowed ranges.','retryable':False},'request_id':request.state.request_id},422)

@app.exception_handler(uploads.UploadError)
async def upload_error(request,exc):
    return JSONResponse({'error':{'code':'invalid_image','message':str(exc),'retryable':False},'request_id':request.state.request_id},exc.status)

def asset_for(asset_id,owner):
    row=db.one('SELECT * FROM assets WHERE id=? AND owner=?',(asset_id,owner))
    if not row:
        fail(404,'asset_not_found','Image not found in this session.')
    return row

def artifact_for(artifact_id,owner):
    row=artifacts.get(artifact_id,owner)
    if not row:
        fail(404,'artifact_not_found','Artifact not found in this session.')
    return row

async def read_upload(file):
    raw=await file.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:
        fail(413,'upload_too_large','Upload limit is 10 MiB.')
    return raw

def asset_public(row):
    return dict(id=row['id'],asset_id=row['id'],geometry=json.loads(row['geometry']),preview_artifact_id=row['clean'],mask_id=row['mask_id'])

@app.get('/api/v1/health')
@app.get('/health')
def health():
    worker=db.one('SELECT * FROM worker_status WHERE id=1')
    return dict(status='ok',mode='real',worker_alive=bool(worker and time.time()-worker['heartbeat']<30))

@app.get('/api/v1/capabilities')
def get_capabilities():
    return capabilities()

@app.get('/api/v1/assets')
def list_assets(request:Request):
    return {'assets':[asset_public(r) for r in db.all_rows('SELECT * FROM assets WHERE owner=? ORDER BY created DESC',(request.state.owner,))]}

@app.post('/api/v1/assets',status_code=201)
async def upload_asset(request:Request,file:UploadFile=File(...)):
    owner=request.state.owner
    if len(db.all_rows('SELECT id FROM assets WHERE owner=?',(owner,)))>=100:
        fail(409,'asset_limit','Delete an existing image before uploading more.')
    raw=await read_upload(file)
    canvas,geometry=uploads.normalize(raw)
    asset_id=str(uuid4())
    directory=private_path(asset_id)
    directory.mkdir()
    original=directory/'original.bin'
    original.write_bytes(raw)
    clean=directory/'clean.png'
    canvas.save(clean)
    original_id=artifacts.add(owner,asset_id,original,'original')
    clean_id=artifacts.add(owner,asset_id,clean,'clean')
    db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?)',(asset_id,owner,json.dumps(geometry),original_id,clean_id,None,time.time()))
    return asset_public(asset_for(asset_id,owner))

@app.put('/api/v1/assets/{asset_id}/mask')
async def put_mask(asset_id:str,request:Request,file:UploadFile=File(...)):
    row=asset_for(asset_id,request.state.owner)
    mask,fraction=uploads.validate_mask(await read_upload(file),json.loads(row['geometry']))
    path=private_path(f'{asset_id}/mask-{uuid4()}.png')
    mask.save(path)
    mask_id=artifacts.add(request.state.owner,asset_id,path,'mask')
    db.execute('UPDATE assets SET mask_id=? WHERE id=?',(mask_id,asset_id))
    return dict(mask_id=mask_id,artifact_id=mask_id,editable_fraction=fraction)

def validate_mask_id(mask_id,asset_id,owner):
    mask=artifact_for(mask_id,owner)
    if mask['asset_id']!=asset_id or mask['kind']!='mask':
        fail(422,'invalid_mask','Choose a mask belonging to this image.')

def require_ready():
    caps=capabilities()
    if not caps['ready']:
        fail(503,'model_unavailable',' '.join(caps['reasons']),True)

def enqueue(owner,asset_id,kind,config):
    try:
        job_id=jobs.enqueue(owner,asset_id,kind,config)
    except ValueError as exc:
        fail(409,'queue_limit',str(exc),True)
    return dict(id=job_id,job_id=job_id,state='queued')

@app.post('/api/v1/assets/{asset_id}/protect',status_code=202)
def protect(asset_id:str,body:ProtectRequest,request:Request):
    asset_for(asset_id,request.state.owner)
    validate_mask_id(body.mask_id,asset_id,request.state.owner)
    require_ready()
    return enqueue(request.state.owner,asset_id,'protect',body.model_dump())

@app.get('/api/v1/jobs/{job_id}')
def get_job(job_id:str,request:Request):
    row=db.one('SELECT * FROM jobs WHERE id=? AND owner=?',(job_id,request.state.owner))
    if not row:
        fail(404,'job_not_found','Job not found in this session.')
    return jobs.public(row)

@app.post('/api/v1/jobs/{job_id}/cancel')
def cancel_job(job_id:str,request:Request):
    row=get_job(job_id,request)
    if row['state'] in ('queued','running'):
        db.execute('UPDATE jobs SET cancel_requested=1, state=CASE WHEN state=\'queued\' THEN \'cancelled\' ELSE state END WHERE id=?',(job_id,))
    return get_job(job_id,request)

@app.post('/api/v1/assets/{asset_id}/edit-tests',status_code=202)
def edit_tests(asset_id:str,body:EditRequest,request:Request):
    asset_for(asset_id,request.state.owner)
    validate_mask_id(body.mask_id,asset_id,request.state.owner)
    job=get_job(body.protection_job_id,request)
    if job['asset_id']!=asset_id or job['kind']!='protect' or job['state']!='succeeded':
        fail(409,'protection_required','Generate a quality-passing protected image first.')
    output=job['output']
    if output['scope']['mask']!=body.mask_id:
        fail(409,'mask_mismatch','Use the same mask as the protection run.')
    if any(s<0 or s>2147483647 for s in body.seeds) or len(set(body.seeds))!=len(body.seeds):
        fail(422,'invalid_seed','Use up to three distinct nonnegative seeds.')
    require_ready()
    return enqueue(request.state.owner,asset_id,'edit',body.model_dump())

@app.get('/api/v1/artifacts/{artifact_id}')
def download(artifact_id:str,request:Request):
    row=artifact_for(artifact_id,request.state.owner)
    if not row['file'].exists():
        fail(404,'artifact_missing','This artifact is no longer available.')
    return FileResponse(row['file'],media_type='image/png' if row['kind']!='original' else 'application/octet-stream',filename=f'imageshield-{row["kind"]}.png' if row['kind']!='original' else 'original.bin')

@app.get('/api/v1/experiments/{experiment_id}')
def get_experiment(experiment_id:str,request:Request):
    row=db.one('SELECT * FROM experiments WHERE id=? AND owner=?',(experiment_id,request.state.owner))
    if not row:
        fail(404,'experiment_not_found','Experiment not found in this session.')
    return dict(id=row['id'],config=json.loads(row['config']),pairs=json.loads(row['pairs']),review=json.loads(row['review']) if row['review'] else None,effectiveness=row['effectiveness'])

@app.put('/api/v1/experiments/{experiment_id}/review')
def review(experiment_id:str,body:ReviewRequest,request:Request):
    experiment=get_experiment(experiment_id,request)
    if sorted(p.seed for p in body.pairs)!=sorted(p['seed'] for p in experiment['pairs']):
        fail(422,'review_mismatch','Review every recorded pair exactly once.')
    if any(p.get('safety_filtered') for p in experiment['pairs']):
        fail(409,'safety_filtered','Safety-filtered outputs are inconclusive and cannot be scored as protection evidence.')
    def usable(score):
        return score.requested_edit_completed=='yes' and score.realism>=4 and score.retained_subject_fidelity>=4
    eligible=[p for p in body.pairs if usable(p.clean)]
    successes=sum(p.protected.requested_edit_completed!='uncertain' and not usable(p.protected) for p in eligible)
    status='inconclusive' if not eligible or any(p.protected.requested_edit_completed=='uncertain' for p in eligible) else ('observed_disruption' if successes else 'bypass_observed')
    record=body.model_dump()|dict(disrupted_pairs=successes,eligible_pairs=len(eligible),image_count=1,rubric='completed=yes, realism>=4, retained fidelity>=4')
    db.execute('UPDATE experiments SET review=?,effectiveness=? WHERE id=?',(json.dumps(record),status,experiment_id))
    return get_experiment(experiment_id,request)

@app.post('/api/v1/verify')
async def verify(request:Request):
    fail(503,'phase_2_unavailable','Signed verification and watermarking are phase 2 and have not been enabled.')

@app.delete('/api/v1/assets/{asset_id}')
def delete_asset(asset_id:str,request:Request):
    asset_for(asset_id,request.state.owner)
    active=None
    with db.connect() as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute("UPDATE jobs SET cancel_requested=1,state=CASE WHEN state='queued' THEN 'cancelled' ELSE state END WHERE asset_id=? AND state IN ('queued','running')",(asset_id,))
        active=con.execute("SELECT id FROM jobs WHERE asset_id=? AND state='running'",(asset_id,)).fetchone()
        if not active:
            for table in ('artifacts','experiments','jobs'):
                con.execute(f'DELETE FROM {table} WHERE asset_id=? AND owner=?',(asset_id,request.state.owner))
            con.execute('DELETE FROM assets WHERE id=? AND owner=?',(asset_id,request.state.owner))
    if active:
        fail(409,'cancellation_pending','Cancellation requested. Retry deletion after the running job stops.',True)
    directory=private_path(asset_id)
    if directory.exists():
        # private_path verifies the resolved absolute target stays inside DATA.
        # Removing the whole owned directory includes unregistered interrupted outputs.
        shutil.rmtree(directory)
    return {'deleted':True}

@app.get('/')
def index():
    return FileResponse(ROOT/'frontend/index.html')

app.mount('/static',StaticFiles(directory=str(ROOT/'frontend'),check_dir=False),name='static')

class BodyLimitMiddleware:
    """Bound chunked uploads before the multipart parser spools their contents."""
    def __init__(self,app):
        self.app=app

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] in ('GET','HEAD','OPTIONS'):
            return await self.app(scope,receive,send)
        chunks=[]
        size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':
                return
            body=message.get('body',b'')
            size+=len(body)
            if size>MAX_BYTES+256*1024:
                response=JSONResponse({'error':dict(code='upload_too_large',message='Upload limit is 10 MiB.',retryable=False),'request_id':str(uuid4())},413)
                return await response(scope,receive,send)
            chunks.append(body)
            if not message.get('more_body',False):
                break
        buffered=b''.join(chunks)
        delivered=False
        async def bounded_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered=True
            return dict(type='http.request',body=buffered,more_body=False)
        return await self.app(scope,bounded_receive,send)

app.add_middleware(BodyLimitMiddleware)
