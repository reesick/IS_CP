"""Portrait demo: DCT-Shield base protection + matched SD1.5 tamper tests.

Phase "protect" runs in .venv-ml; phase "edit" can run in either ML env.
Writes outputs/portrait-demo/progress.json so the dashboard can show progress.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'outputs/portrait-demo'
PROMPT='a smiling man wearing round sunglasses, realistic studio portrait photograph'
SEED=11

def status(**fields):
    path=OUT/'progress.json';previous={}
    try:previous=json.loads(path.read_text())
    except (OSError,ValueError):pass
    previous.update(fields,updated_at=time.time())
    shown={k:v for k,v in fields.items() if k in ('phase','stage','completed','total','objective','error','state')}
    print(time.strftime('%H:%M:%S'),'[portrait]',' | '.join(f'{k}={round(v,2) if isinstance(v,float) else v}' for k,v in shown.items()),flush=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(previous));tmp.replace(path)

def prepare():
    from PIL import Image,ImageDraw
    src=Image.open(OUT/'source.png').convert('RGB')
    scale=min(512/src.width,512/src.height)
    w,h=round(src.width*scale),round(src.height*scale)
    canvas=Image.new('RGB',(512,512),(244,244,245))
    x0,y0=(512-w)//2,(512-h)//2
    canvas.paste(src.resize((w,h),Image.Resampling.LANCZOS),(x0,y0))
    canvas.save(OUT/'clean.png')
    # Editable region: the face, eyebrows to chin (normalised source coordinates).
    mask=Image.new('L',(512,512),0)
    box=(x0+round(.26*w),y0+round(.27*h),x0+round(.76*w),y0+round(.97*h))
    ImageDraw.Draw(mask).rectangle(box,fill=255)
    mask.save(OUT/'edit-mask.png')
    return box

def protect(steps):
    from backend.app.ml.dct_shield import protect as dct_protect
    from backend.app.services.metrics import measure
    box=prepare()
    (OUT/'progress.json').unlink(missing_ok=True)
    status(phase='protect',stage='Optimising DCT coefficients',completed=0,total=steps,started_at=time.time(),state='running')
    def tick(item):status(phase='protect',stage='Optimising DCT coefficients',completed=item['completed'],total=item['total'],objective=item['objective'])
    result=dct_protect(OUT/'clean.png',OUT/'protected.png',steps=steps,progress=tick)
    result['fidelity']=measure(OUT/'clean.png',OUT/'protected.png',8/255)
    result['mask_box']=box;result['prompt']=PROMPT;result['seed']=SEED
    (OUT/'results.json').write_text(json.dumps(result,indent=2,default=str))
    status(phase='protect',stage='Protection saved',completed=steps,total=steps)

def edit(offload):
    from backend.app.ml.editor import edit_pair
    result=json.loads((OUT/'results.json').read_text())
    config=dict(prompt=PROMPT,seeds=[SEED])
    if offload:config.update(sequential_component_load=True,inference_cpu_offload=True)
    for channel in ('local_png','jpeg_simulation'):
        label='PNG' if channel=='local_png' else 'JPEG-85'
        def tick(done,total,stage,label=label):status(phase='edit',stage=f'{stage} ({label})',completed=done,total=total)
        result['paired_'+channel]=edit_pair(OUT/'clean.png',OUT/'protected.png',OUT/'edit-mask.png',OUT/channel,dict(config,channel=channel),tick)
        (OUT/'results.json').write_text(json.dumps(result,indent=2,default=str))
    status(phase='done',stage='Portrait demo complete',state='done',finished_at=time.time())

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['protect','edit'])
    parser.add_argument('--steps',type=int,default=1000)
    parser.add_argument('--offload',action='store_true')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    try:
        protect(args.steps) if args.phase=='protect' else edit(args.offload)
    except BaseException as exc:
        traceback.print_exc();status(state='failed',error=f'{type(exc).__name__}: {exc}');raise
