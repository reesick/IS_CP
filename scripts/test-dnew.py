"""Run local uploaded-image protection and matched edit tests; export a tamper kit."""
import argparse
import html
import io
import json
from pathlib import Path
import time

import httpx
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='outputs/dnew-tests/2026-10-28')
    args=parser.parse_args()
    out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'outputs'):
        raise SystemExit('Test exports must stay under the private ignored outputs directory.')
    out.mkdir(parents=True,exist_ok=True)
    samples=json.loads((ROOT/'data/dnew-tests/samples.json').read_text())
    report=dict(purpose='Real local images, known-mask 20-iteration execution and fidelity tests; effectiveness requires review',images=[],started=time.time())
    session_dir=ROOT/'data/dnew-tests'
    with httpx.Client(base_url='http://127.0.0.1:8000/api/v1',timeout=45) as client:
        def checked(response):
            response.raise_for_status()
            return response.json()
        def persist():
            (out/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            (session_dir/'session.json').write_text(json.dumps(dict(cookies=dict(client.cookies))),encoding='utf-8')
        def wait(job_id):
            start=time.monotonic()
            previous=''
            while time.monotonic()-start<1800:
                job=checked(client.get('/jobs/'+job_id))
                current=f'{job["state"]}: {job["stage"]}'
                if current!=previous:
                    print(current,flush=True);previous=current
                if job['state'] not in ('queued','running'):
                    return job
                time.sleep(.7)
            raise RuntimeError('Test job exceeded its deadline.')
        def download(artifact_id,path):
            response=client.get('/artifacts/'+artifact_id)
            response.raise_for_status()
            path.write_bytes(response.content)
            with Image.open(io.BytesIO(response.content)) as image:
                assert image.format=='PNG' and image.size==(512,512)
        for index,sample in enumerate(samples,1):
            source=Path(sample['path'])
            directory=out/f'{index:02d}'
            directory.mkdir(exist_ok=True)
            print(f'IMAGE {index}: {sample["label"]}',flush=True)
            raw=source.read_bytes()
            asset=checked(client.post('/assets',files={'file':(source.name,raw,'image/png' if source.suffix.lower()=='.png' else 'image/jpeg')}))
            download(asset['preview_artifact_id'],directory/'clean.png')
            mask=Image.new('L',(512,512),0)
            x1,y1,x2,y2=sample['rectangle_512']
            ImageDraw.Draw(mask).rectangle((x1,y1,x2-1,y2-1),fill=255)
            mask.save(directory/'edit-mask.png')
            mask_bytes=io.BytesIO();mask.save(mask_bytes,'PNG')
            mask_id=checked(client.put('/assets/'+asset['id']+'/mask',files={'file':('mask.png',mask_bytes.getvalue(),'image/png')}))['mask_id']
            entry=dict(sample=sample,asset_id=asset['id'],geometry=asset['geometry'],attempts=[],effectiveness='not_tested')
            report['images'].append(entry)
            for budget in (4,2,1):
                submission=checked(client.post('/assets/'+asset['id']+'/protect',json=dict(mask_id=mask_id,method='diffusionguard',profile='smoke',seed=42,epsilon=budget/255)))
                job=wait(submission['id'])
                entry['attempts'].append(job)
                persist()
                if job['state']=='succeeded':
                    entry['protection']=job
                    download(job['output']['artifacts']['protected'],directory/'protected.png')
                    break
                if job['state']=='rejected_quality':
                    download(job['output']['artifacts']['diagnostic'],directory/f'REJECTED-quality-budget-{budget}.png')
                else:
                    raise RuntimeError(f'Protection failed: {job.get("error_code")}')
            if not entry.get('protection'):
                entry['status']='all_budgets_rejected'
                persist();continue
            protection=entry['protection']
            test=checked(client.post('/assets/'+asset['id']+'/edit-tests',json=dict(protection_job_id=protection['id'],mask_id=mask_id,prompt=sample['prompt'],editor='sd15_inpaint',seeds=[11],channel='local_png')))
            edit=wait(test['id'])
            entry['edit_job']=edit
            if edit['state']=='succeeded':
                experiment=checked(client.get('/experiments/'+edit['output']['experiment_id']))
                entry['experiment']=experiment
                pair=experiment['pairs'][0]
                for name in ('edit_clean','edit_protected'):
                    download(pair[name],directory/(name+'.png'))
                entry['status']='ready_for_review'
                entry['effectiveness']='inconclusive'
            else:
                entry['status']='edit_failed'
            persist()
    report['finished']=time.time()
    persist()
    cards=[]
    for index,entry in enumerate(report['images'],1):
        parts=[f'<section><h2>{html.escape(entry["sample"]["label"])}</h2>',f'<p>{html.escape(entry["sample"]["prompt"])}</p>']
        if entry.get('protection'):
            q=entry['protection']['output']['quality']
            parts.append(f'<p>PSNR {q["psnr_db"]:.2f} dB · SSIM {q["ssim"]:.4f} · effectiveness unreviewed</p>')
        parts.append('<div class="grid">')
        for name,label in [('clean','Clean reference'),('protected','Protected — download to tamper'),('edit_clean','AI edit of clean'),('edit_protected','AI edit of protected')]:
            if (out/f'{index:02d}/{name}.png').exists():
                parts.append(f'<figure><a href="{index:02d}/{name}.png" download><img src="{index:02d}/{name}.png" alt="{label}"></a><figcaption>{label}</figcaption></figure>')
        parts.append('</div></section>');cards.append(''.join(parts))
    page='<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ImageShield local test kit</title><style>body{font:15px system-ui;background:#fafafa;color:#171717;max-width:1120px;margin:40px auto;padding:20px}section{border-top:1px solid #ddd;margin-top:32px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}figure{margin:0;background:white;border:1px solid #ddd;padding:12px}img{width:100%;height:auto}figcaption{margin-top:8px}@media(max-width:600px){.grid{grid-template-columns:1fr}}</style><h1>Your local tamper test kit</h1><p>Sources remain unchanged. All exports use the 512 × 512 research canvas. Click Protected to download, then tamper with a copy. The mask and paired editor settings are recorded in results.json. These runs verify execution and fidelity, not universal AI edit resistance. Manual editing remains possible.</p>'+''.join(cards)
    (out/'index.html').write_text(page,encoding='utf-8')
    print('RESULTS '+str(out),flush=True)

if __name__=='__main__':
    main()
