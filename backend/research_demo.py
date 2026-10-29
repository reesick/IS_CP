"""Local research workspace. Saved examples are passive; playground runs are explicit."""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import time
from typing import Literal
from uuid import uuid4
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from PIL import Image,ImageChops,ImageFilter

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/'frontend/research-demo'
FILES={}
PLAYFILES={}
PLAYSTATE={'status':'idle'}
RUNTIME=None
ACTIVE_TASK=None
ACTIVE_CANCEL=None

def mask_preview(case,source,mask):
    destination=ROOT/'outputs/dashboard-previews'/f'{case}-mask.png'
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.is_file() and destination.stat().st_mtime>=max(Path(source).stat().st_mtime,Path(mask).stat().st_mtime):return destination
    with Image.open(source) as opened:photo=opened.convert('RGBA')
    with Image.open(mask) as opened:region=opened.convert('L')
    if photo.size!=region.size:raise RuntimeError('Mask and image dimensions differ.')
    color=Image.new('RGBA',photo.size,(55,215,241,0))
    color.putalpha(region.point(lambda value:round(value*.32)))
    preview=Image.alpha_composite(photo,color)
    border=ImageChops.subtract(region.filter(ImageFilter.MaxFilter(3)),region.filter(ImageFilter.MinFilter(3)))
    outline=Image.new('RGBA',photo.size,(90,235,255,0));outline.putalpha(border)
    temporary=destination.with_name(f'{case}-{uuid4().hex}.tmp')
    Image.alpha_composite(preview,outline).convert('RGB').save(temporary,format='PNG')
    temporary.replace(destination)
    return destination

def perturbation_preview(case,clean,candidate):
    """Real |protected - original| per pixel, amplified so the pattern is visible."""
    import numpy as np
    with Image.open(clean) as a:a=a.convert('RGB')
    with Image.open(candidate) as b:b=b.convert('RGB')
    if a.size!=b.size:b=b.resize(a.size,Image.Resampling.LANCZOS)
    delta=np.abs(np.asarray(a,dtype=np.int16)-np.asarray(b,dtype=np.int16)).max(axis=2).astype(np.float32)
    ceiling=float(np.percentile(delta,99.5)) or 1.0
    gain=255.0/ceiling
    level=np.clip(delta*gain,0,255)/255.0
    heat=np.stack([level*55,level*215,level*241],axis=2)+np.stack([level**3*200]*3,axis=2)
    destination=ROOT/'outputs/dashboard-previews'/f'{case}-perturbation.png'
    destination.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.clip(heat,0,255).astype('uint8')).save(destination)
    changed=float((delta>0).mean())
    return destination,dict(max_255=int(delta.max()),mean_255=round(float(delta.mean()),2),changed_pct=round(changed*100,1),gain=round(gain,1))

def verdict_preview(case,clean_edit,candidate_edit):
    with Image.open(clean_edit) as a:a=a.convert('RGB')
    with Image.open(candidate_edit) as b:b=b.convert('RGB').resize(a.size)
    canvas=Image.new('RGB',(a.width*2+12,a.height),(8,8,8))
    canvas.paste(a,(0,0));canvas.paste(b,(a.width+12,0))
    destination=ROOT/'outputs/dashboard-previews'/f'{case}-verdict.png'
    canvas.save(destination)
    return destination

def editable_share(mask):
    import numpy as np
    with Image.open(mask) as m:region=np.asarray(m.convert('L'))
    return round(float((region>127).mean())*100,1)

def load_json(relative):return json.loads((ROOT/relative).read_text())

def example(case,label,method,prompt,quality,pair,mask):
    mapping={'clean_input':pair['clean_input'],'candidate_input':pair['protected_input'],'edit_clean':pair['edit_clean'],'edit_candidate':pair['edit_protected'],'mask':str(mask)}
    images={}
    for key,value in mapping.items():
        path=Path(value).resolve()
        if not path.is_relative_to(ROOT/'outputs') or not path.is_file():raise RuntimeError('Saved example file is unavailable: '+key)
        FILES[case,key]=path;images[key]=f'/artifact/{case}/{key}'
    FILES[case,'mask_overlay']=mask_preview(case,mapping['clean_input'],mask)
    images['mask_overlay']=f'/artifact/{case}/mask_overlay'
    return dict(id=case,label=label,method=method,prompt=prompt,seed=pair['seed'],channel='local_png',safety_filtered=pair.get('safety_filtered',False),quality_gate=quality,images=images,source='previously measured local experiment',effectiveness='not_a_general_protection_claim')

dct=load_json('outputs/research-2026-10-28/dct-shield/results.json')
pg=load_json('outputs/research-2026-10-28/paper-baselines/results.json')
tshirt=load_json('outputs/dnew-tests/2026-10-28/results.json')['images'][0]
base=ROOT/'outputs/dnew-tests/2026-10-28'
tshirt_pair=dict(seed=11,safety_filtered=tshirt['experiment']['pairs'][0]['safety_filtered'],clean_input=str(base/'01/clean.png'),protected_input=str(base/'01/protected.png'),edit_clean=str(base/'01/edit_clean.png'),edit_protected=str(base/'01/edit_protected.png'))
EXAMPLES=[
    example('shorts','Shorts','DCT-Shield base',dct['paired_local_png']['prompt'],dct['product_quality_diagnostic']['gate'],dct['paired_local_png']['pairs'][0],base/'03/edit-mask.png'),
    example('cap','Cap','PhotoGuard encoder',pg['photoguard_paired']['prompt'],pg['photoguard_quality']['gate'],pg['photoguard_paired']['pairs'][0],base/'02/edit-mask.png'),
    example('tshirts','T-shirts','DiffusionGuard smoke',tshirt['experiment']['config']['prompt'],tshirt['protection'].get('output',{}).get('quality',{}).get('gate','unreviewed'),tshirt_pair,base/'01/edit-mask.png'),
]
protection=tshirt['protection']['output']
qualities={'shorts':dct['product_quality_diagnostic'],'cap':pg['photoguard_quality'],'tshirts':protection['quality']}
prov=protection.get('provenance',{})
def fmt_seconds(value):
    if not value:return 'not recorded'
    value=float(value);return f"{value:.0f} s" if value<120 else f"{value/60:.1f} min"
def dct_method(res,verdict):
    return dict(
        prep=('Transform','JPEG DCT transform','Convert RGB to YCbCr, subsample colour 4:2:0, split into 8x8 blocks and take the DCT. The defence edits these frequency coefficients, not raw pixels.',
              'RGB  >  YCbCr 4:2:0  >  8x8 blocks  >  DCT  >  quantise (q95)',
              [('Colour space','YCbCr, 4:2:0'),('Block size','8 x 8'),('JPEG quality',f"{res.get('quality',0.95)*100:.0f}")]),
        opt=('Coefficient optimisation',f"{res['steps']:,} gradient steps push the SD1.5 VAE latent toward zero by nudging DCT coefficients. No RGB cap exists in this method, which is why noise can be visible.",
             [('Objective','Minimise VAE latent norm'),('Steps',f"{res['steps']:,}"),('Coefficient bound',f"+/- {res.get('coefficient_epsilon',1.0):g}"),('Step size',f"{res.get('coefficient_step',0.1):g}"),('RGB budget','None'),('Runtime',fmt_seconds(res.get('elapsed_seconds')))]),
        verdict=verdict)
METHOD={
    'shorts':dct_method(dct,('Disrupted','good','The control edit gives normal green shorts; the protected edit comes out with a distorted pose and body. Seen on SD1.5 with PNG input. JPEG-85 restored a normal edit.')),
    'cap':dict(
        prep=('Encode','VAE encoding','Pass the whole image through the frozen SD1.5 VAE encoder. PhotoGuard attacks this latent so the editor starts from a corrupted representation.',
              'image x  >  VAE encoder  >  latent z   (target: z = 0)',
              [('Encoder','SD1.5 inpainting VAE (frozen)'),('Mask used','No, whole image'),('Source commit',str(pg['photoguard'].get('source_commit',''))[:10])]),
        opt=('Encoder attack (PGD)',f"{pg['photoguard']['iterations']:,} projected gradient steps move the VAE posterior mean toward the zero latent, clipped to the RGB budget each step.",
             [('Objective','L2 norm of latent toward zero'),('Steps',f"{pg['photoguard']['iterations']:,}"),('RGB budget',f"{pg['photoguard']['epsilon_rgb']*255:.1f}/255"),('Step size',f"{pg['photoguard'].get('step_normalized',0.02):g} (normalised, linear decay)"),('Loss',f"{pg['photoguard'].get('loss_initial',0):.0f} > {pg['photoguard'].get('loss_final',0):.0f}"),('Runtime',fmt_seconds(pg['photoguard'].get('elapsed_seconds')))]),
        verdict=('Not disrupted','bad','Both edits still produce a green cap. Framing and background shifted, but the requested edit worked.')),
    'tshirts':dict(
        prep=('Load model','Load frozen editor','Load SD1.5 inpainting with frozen weights and the audited DiffusionGuard code. Only the image pixels are allowed to change.',
              'SD1.5 inpainting UNet (frozen)  +  known mask  >  pixel gradients',
              [('Editor','SD1.5 inpainting, fp16'),('Upstream commit',str(prov.get('upstream_commit',''))[:10] or 'pinned'),('Mask policy','Single known mask')]),
        opt=('DiffusionGuard optimisation',f"{prov.get('iterations',20)} gradient steps (smoke profile) target the denoiser's early noise prediction inside the mask. Every step is clipped to the RGB budget.",
             [('Objective','Disrupt early noise prediction in mask'),('Steps',f"{prov.get('iterations',20)} (research profile: 800)"),('RGB budget',f"{prov.get('epsilon_rgb',2/255)*255:g}/255"),('Seed',str(prov.get('seed',42))),('Runtime',fmt_seconds(protection.get('elapsed_seconds')))]),
        verdict=('Not established','neutral','Fidelity passed, but both edits look plausible. The 20-step smoke profile shows no clear disruption.')),
}
def attach_pipeline(item,q,m):
    case=item['id']
    perturb_path,perturb=perturbation_preview(case,FILES[case,'clean_input'],FILES[case,'candidate_input'])
    FILES[case,'perturbation']=perturb_path;item['images']['perturbation']=f'/artifact/{case}/perturbation'
    FILES[case,'verdict']=verdict_preview(case,FILES[case,'edit_clean'],FILES[case,'edit_candidate']);item['images']['verdict']=f'/artifact/{case}/verdict'
    share=editable_share(FILES[case,'mask'])
    passed=q.get('gate')=='passed'
    item['perturbation']=perturb
    item['verdict']=dict(zip(('label','tone','text'),m['verdict']))
    img=item['images']
    item['pipeline']=[
        dict(phase='Prepare',short='Original',title='Original photo',image=img['clean_input'],image_label='Clean original, 512 x 512',
             detail='The source photo is converted to RGB and fitted to a 512 x 512 canvas. This clean copy is never modified and is the reference for every comparison.',
             specs=[('Canvas','512 x 512 RGB'),('Role','Clean reference')]),
        dict(phase='Prepare',short='Edit region',title='Editable region',image=img['mask_overlay'],image_label='Cyan = area the attacker edits',
             detail='The mask marks where an attacker would edit. The same mask is used for both tamper tests so only the protection differs.',
             specs=[('Editable area',f"{share}% of pixels"),('Mask rule','White = editable, black = kept')]),
        dict(phase='Protect',short=m['prep'][0],title=m['prep'][1],image=None,formula=m['prep'][3],image_label='Internal representation, no image saved',
             detail=m['prep'][2],specs=m['prep'][4]),
        dict(phase='Protect',short='Optimise',title=m['opt'][0],image=img['perturbation'],image_label=f"Real pixel change map, amplified x{perturb['gain']:g} to be visible",
             detail=m['opt'][1]+' The map shows exactly which pixels moved and by how much.',specs=m['opt'][2]+[('Pixels changed',f"{perturb['changed_pct']}%"),('Largest change',f"{perturb['max_255']}/255"),('Average change',f"{perturb['mean_255']}/255")]),
        dict(phase='Protect',short='Protected PNG',title='Protected image',image=img['candidate_input'],image_label='Protected candidate as saved',
             detail='The optimised image is saved as a lossless PNG. To the eye it should look like the original; the difference is the pattern in the previous step.',
             specs=[('Format','PNG, lossless'),('Metadata','EXIF dropped')]),
        dict(phase='Verify',short='Quality check',title='Invisibility check',image=img['candidate_input'],image_label='Image measured against the original',
             detail='The saved file is compared with the original. All checks must pass for the image to count as invisible protection.',
             specs=[('PSNR',f"{q['psnr_db']:.2f} dB (need 35+)"),('SSIM',f"{q['ssim']:.4f} (need 0.98+)"),('Max change',f"{q['max_absolute_difference']*255:.0f}/255"),('Result','Passed' if passed else 'Failed, visible noise')],
             status='pass' if passed else 'fail'),
        dict(phase='Attack',short='Tamper original',title='Tamper the original (control)',image=img['edit_clean'],image_label='SD1.5 edit of the clean original',
             detail='SD1.5 inpainting edits the clean image. This shows what a normal, successful edit looks like.',
             specs=[('Prompt',item['prompt']),('Seed',str(item['seed'])),('Sampler','DDIM, 30 steps'),('CFG / strength','7.5 / 0.99')]),
        dict(phase='Attack',short='Tamper protected',title='Tamper the protected image',image=img['edit_candidate'],image_label='Same edit on the protected image',
             detail='Exactly the same prompt, mask, seed and settings, now on the protected image. Any difference comes from the perturbation.',
             specs=[('Prompt','Same as control'),('Seed',str(item['seed'])),('Channel','PNG (no compression)')]),
        dict(phase='Result',short='Verdict',title='Compare the edits',image=img['verdict'],image_label='Left: control edit  |  Right: protected edit',
             detail=item['verdict']['text'],specs=[('Outcome',item['verdict']['label']),('Fidelity','Passed' if passed else 'Failed'),('Scope','SD1.5 inpainting only')],
             status=item['verdict']['tone']),
    ]
    for step in item['pipeline']:step['specs']=[list(pair) for pair in step['specs']]

for item in EXAMPLES:attach_pipeline(item,qualities[item['id']],METHOD[item['id']])

PORTRAIT=ROOT/'outputs/portrait-demo'
PORTRAIT_PROMPT='a smiling man wearing round sunglasses, realistic studio portrait photograph'
def portrait_preview():
    """Face sample available immediately: clean canvas + face mask (CPU only)."""
    from PIL import ImageDraw
    source=PORTRAIT/'source.png'
    if not source.is_file():return None
    clean,mask=PORTRAIT/'clean.png',PORTRAIT/'edit-mask.png'
    if not clean.is_file() or not mask.is_file():
        with Image.open(source) as opened:src=opened.convert('RGB')
        scale=min(512/src.width,512/src.height);w,h=round(src.width*scale),round(src.height*scale)
        canvas=Image.new('RGB',(512,512),(244,244,245));x0,y0=(512-w)//2,(512-h)//2
        canvas.paste(src.resize((w,h),Image.Resampling.LANCZOS),(x0,y0));canvas.save(clean)
        region=Image.new('L',(512,512),0)
        ImageDraw.Draw(region).rectangle((x0+round(.26*w),y0+round(.27*h),x0+round(.76*w),y0+round(.97*h)),fill=255);region.save(mask)
    FILES['portrait','clean_input']=clean;FILES['portrait','mask']=mask
    FILES['portrait','mask_overlay']=mask_preview('portrait',clean,mask)
    images=dict(clean_input='/artifact/portrait/clean_input',mask='/artifact/portrait/mask',mask_overlay='/artifact/portrait/mask_overlay')
    protected=PORTRAIT/'protected.png'
    if protected.is_file() and protected.stat().st_size>0:
        FILES['portrait','candidate_input']=protected;images['candidate_input']='/artifact/portrait/candidate_input'
    else:FILES.pop(('portrait','candidate_input'),None)
    return dict(id='portrait',label='Portrait',method='DCT-Shield base',prompt=PORTRAIT_PROMPT,seed=11,ready='candidate_input' in images,images=images)
def load_portrait():
    """Add the portrait sample once its background run has saved matched edits."""
    if any(e['id']=='portrait' for e in EXAMPLES):return
    try:res=json.loads((PORTRAIT/'results.json').read_text())
    except (OSError,ValueError):return
    pair=(res.get('paired_local_png') or {}).get('pairs',[None])[0]
    if not pair:return
    item=example('portrait','Portrait','DCT-Shield base',res['prompt'],res['fidelity']['gate'],pair,PORTRAIT/'edit-mask.png')
    jpeg=(res.get('paired_jpeg_simulation') or {}).get('pairs',[None])[0]
    if jpeg:
        for key,source in (('jpeg_edit_clean','edit_clean'),('jpeg_edit_candidate','edit_protected')):
            path=Path(jpeg[source]).resolve()
            if path.is_relative_to(ROOT/'outputs') and path.is_file():FILES['portrait',key]=path;item['images'][key]=f'/artifact/portrait/{key}'
    attach_pipeline(item,res['fidelity'],dct_method(res,('Disrupted','good','The control edit gives a clean smiling face; the protected edit comes out blurred, washed out and distorted. Seen on SD1.5 with PNG input. Saving as JPEG-85 removed the effect, and the protected input failed the fidelity gate (PSNR 27.2 dB).')))
    EXAMPLES.append(item)

@asynccontextmanager
async def lifespan(app):
    async def upkeep():
        while True:
            await asyncio.sleep(15)
            if RUNTIME is not None and PLAYSTATE['status']!='running':await asyncio.to_thread(RUNTIME.trim_idle)
    task=asyncio.create_task(upkeep())
    try:yield
    finally:
        task.cancel()
        if ACTIVE_CANCEL:ACTIVE_CANCEL.touch()
        if ACTIVE_TASK:ACTIVE_TASK.cancel()
        if RUNTIME is not None:await asyncio.to_thread(RUNTIME.close)

app=FastAPI(title='ImageShield workspace',lifespan=lifespan,docs_url=None,redoc_url=None)

@app.middleware('http')
async def local_security(request:Request,call_next):
    if request.url.hostname not in ('127.0.0.1','localhost','::1','testserver'):
        return JSONResponse({'detail':'Use the loopback address.'},status_code=400)
    if request.method not in ('GET','HEAD'):
        if request.method!='POST' or request.url.path!='/api/playground/run':return JSONResponse({'detail':'Method unavailable.'},status_code=405)
        if request.headers.get('origin') and request.headers['origin']!=str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'Cross-origin requests are blocked.'},status_code=403)
        try:length=int(request.headers.get('content-length','0'))
        except ValueError:length=10000
        if length>4096:return JSONResponse({'detail':'Request too large.'},status_code=413)
    response=await call_next(request)
    response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response

@app.get('/')
def home():return FileResponse(FRONTEND/'landing.html')

@app.get('/dashboard')
def dashboard():return FileResponse(FRONTEND/'index.html')

@app.get('/api/state')
def state():return {'status':'preloaded','example_count':len(EXAMPLES)}

@app.get('/api/examples')
def examples():
    load_portrait()
    full=any(e['id']=='portrait' for e in EXAMPLES)
    pending=[] if full else [p for p in [portrait_preview()] if p]
    return {'examples':EXAMPLES,'pending':pending}

@app.get('/api/background')
def background():
    try:state=json.loads((PORTRAIT/'progress.json').read_text())
    except (OSError,ValueError):state={'state':'not_started'}
    return {**state,'now':time.time(),'loaded':any(e['id']=='portrait' for e in EXAMPLES)}

@app.get('/artifact/{case}/{key}')
def artifact(case:str,key:str):
    path=FILES.get((case,key))
    if path is None:raise HTTPException(404,'Image unavailable.')
    return FileResponse(path,media_type='image/png')

class PlaygroundEdit(BaseModel):
    sample:Literal['shorts','cap','tshirts','portrait']='shorts'
    prompt:str=Field(min_length=1,max_length=500)
    seed:int=Field(default=11,strict=True,ge=0,le=2**32-1)
    channel:Literal['local_png','jpeg_simulation']='local_png'

@app.get('/api/playground/state')
def playground_state():return {**PLAYSTATE,'now':time.time()}

@app.get('/playground/artifact/{job_id}/{kind}')
def playground_image(job_id:str,kind:str):
    path=PLAYFILES.get(job_id,{}).get(kind)
    if path is None or not path.is_file():raise HTTPException(404,'Result unavailable.')
    return FileResponse(path,media_type='image/png')

async def execute_playground(job_id,folder,request_path,cancel_path,sample):
    global PLAYSTATE,RUNTIME
    try:
        if RUNTIME is None:
            from backend.app.ml_runtime import MLRuntime
            RUNTIME=MLRuntime()
        process=RUNTIME.submit(request_path);started=time.monotonic();last=None
        print(f"[playground] job {job_id[:8]} started · sample={sample} · model {'warm' if PLAYSTATE.get('warm') else 'cold, loading SD1.5'}",flush=True)
        while not (folder/'result.json').exists():
            if process.poll() is not None:raise RuntimeError('Model process exited. Check available system memory and retry.')
            if time.monotonic()-started>300:
                cancel_path.touch();await asyncio.to_thread(RUNTIME.close)
                raise RuntimeError('The local test exceeded five minutes.')
            progress=folder/'progress.json'
            if progress.exists():
                try:p=json.loads(progress.read_text())
                except (ValueError,OSError):p=None
                if p and (p['stage'],p['completed_steps'])!=last:
                    last=(p['stage'],p['completed_steps']);print(f"[playground] {time.monotonic()-started:6.1f}s  {p['stage']}  step {p['completed_steps']}/{p['total_steps']}",flush=True)
                if p:PLAYSTATE.update(phase='editing',stage=p['stage'],completed=p['completed_steps'],total=p['total_steps'],progress=f"{p['stage']} ({p['completed_steps']}/{p['total_steps']})")
            await asyncio.sleep(.5)
        receipt=json.loads((folder/'result.json').read_text())
        if not receipt['ok']:
            await asyncio.to_thread(RUNTIME.close)
            raise RuntimeError(receipt.get('error_message','Model execution failed.'))
        output=receipt['output'];pair=output['pairs'][0];images={};allowed={}
        for key,source in {'clean_input':'clean_input','candidate_input':'protected_input','edit_clean':'edit_clean','edit_candidate':'edit_protected'}.items():
            path=Path(pair[source]).resolve()
            if path.parent!=folder.resolve() or not path.is_file():raise RuntimeError('Unexpected result file.')
            allowed[key]=path;images[key]=f'/playground/artifact/{job_id}/{key}'
        PLAYFILES[job_id]=allowed
        while len(PLAYFILES)>8:PLAYFILES.pop(next(iter(PLAYFILES)))
        (folder/'experiment.json').write_text(json.dumps(output,indent=2))
        RUNTIME.mark_idle();print(f"[playground] job {job_id[:8]} completed in {time.monotonic()-started:.1f}s · outputs in {folder}",flush=True)
        PLAYSTATE={'status':'completed','job_id':job_id,'started_at':PLAYSTATE.get('started_at'),'finished_at':time.time(),'warm':PLAYSTATE.get('warm',False),'result':dict(sample=sample,prompt=output['prompt'],seed=pair['seed'],channel=output['channel'],safety_filtered=pair['safety_filtered'],images=images,runtime_seconds=round(time.time()-PLAYSTATE.get('started_at',time.time()),1),warm=PLAYSTATE.get('warm',False))}
    except asyncio.CancelledError:
        cancel_path.touch();raise
    except Exception as exc:
        if RUNTIME is not None:await asyncio.to_thread(RUNTIME.close)
        print(f"[playground] job {job_id[:8]} FAILED: {exc}",flush=True)
        PLAYSTATE={'status':'failed','job_id':job_id,'error':str(exc),'started_at':PLAYSTATE.get('started_at'),'finished_at':time.time()}

@app.post('/api/playground/run',status_code=202)
async def playground_run(edit:PlaygroundEdit):
    global PLAYSTATE,ACTIVE_TASK,ACTIVE_CANCEL
    if PLAYSTATE['status']=='running':raise HTTPException(409,'A local test is already running.')
    if not edit.prompt.strip():raise HTTPException(422,'Enter an edit prompt.')
    if (edit.sample,'candidate_input') not in FILES:raise HTTPException(409,'Protection for this sample is still running. Wait for the protected image.')
    job_id=str(uuid4());folder=ROOT/'outputs/playground'/job_id;folder.mkdir(parents=True)
    ACTIVE_CANCEL=folder/'cancel';request_path=folder/'request.json'
    request_path.write_text(json.dumps(dict(kind='edit',clean_path=str(FILES[edit.sample,'clean_input']),protected_path=str(FILES[edit.sample,'candidate_input']),mask_path=str(FILES[edit.sample,'mask']),output_dir=str(folder),config=dict(prompt=edit.prompt.strip(),seeds=[edit.seed],channel=edit.channel,sequential_component_load=True,inference_cpu_offload=True),progress_path=str(folder/'progress.json'),cancel_path=str(ACTIVE_CANCEL),result_path=str(folder/'result.json'))))
    warm=RUNTIME is not None and RUNTIME.process is not None and RUNTIME.process.poll() is None
    PLAYSTATE={'status':'running','job_id':job_id,'phase':'loading','stage':'Loading SD1.5 model' if not warm else 'Preparing edit','completed':0,'total':0,'warm':warm,'started_at':time.time(),'progress':'Loading local SD1.5 and running matched edits…'}
    ACTIVE_TASK=asyncio.create_task(execute_playground(job_id,folder,request_path,ACTIVE_CANCEL,edit.sample))
    return PLAYSTATE

app.mount('/static',StaticFiles(directory=FRONTEND),name='static')
