"""Three local experimental candidates for USER-run frontier editor testing.

No remote image inference. A quality pass is not an effectiveness claim.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys
import zipfile
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from backend.app.ml.contrastive_probe import protect_batch
from backend.app.services.metrics import measure
parser=argparse.ArgumentParser()
parser.add_argument('--steps',type=int,default=5000)
parser.add_argument('--epsilon-levels',type=float,default=2)
parser.add_argument('--out',type=Path,default=ROOT/'outputs/frontier-test-kit/2026-10-29')
parser.add_argument('--publish-downloads',action='store_true')
parser.add_argument('--initial-dir',type=Path,help='Refine a prior aligned kit attempt; hashes of clean references must match.')
args=parser.parse_args()
out=args.out
archive=out.with_suffix('.zip')
downloads=Path.home()/'Downloads'/'ImageShield_Frontier_Test_Kit_2026-10-29'
download_archive=downloads.parent/'ImageShield_Frontier_Test_Kit_2026-10-29.zip'
if out.exists() and any(out.iterdir()):raise FileExistsError('Use a new empty output folder; previous research evidence is preserved: '+str(out))
if archive.exists():raise FileExistsError('Refusing to overwrite an existing kit archive: '+str(archive))
if args.publish_downloads and (downloads.exists() or download_archive.exists()):raise FileExistsError('Downloads already contains this kit; choose a new destination before running.')
out.mkdir(parents=True,exist_ok=True)
samples=json.loads((ROOT/'data/dnew-tests/samples.json').read_text())
labels=['tshirts','cap','shorts']
sources=[];destinations=[];records=[]
for i,(sample,label) in enumerate(zip(samples,labels),1):
    source=out/'clean-references'/f'{i:02d}-{label}-clean.png';source.parent.mkdir(exist_ok=True)
    with Image.open(sample['path']) as opened:
        image=ImageOps.exif_transpose(opened).convert('RGB');original_size=list(image.size)
        image.thumbnail((1024,1024),Image.Resampling.LANCZOS);image.save(source)
    destination=out/f'{i:02d}-{label}-protected-EXPERIMENTAL.png'
    sources.append(source);destinations.append(destination)
    records.append(dict(label=sample['label'],source_original_size=original_size,clean_reference=str(source.relative_to(out)),candidate=destination.name))
initial_paths=None
if args.initial_dir:
    prior=json.loads((args.initial_dir/'manifest.json').read_text())
    if len(prior['images'])!=len(sources):raise ValueError('Prior attempt does not contain the same source count.')
    initial_paths=[]
    for source,entry in zip(sources,prior['images']):
        if hashlib.sha256(source.read_bytes()).hexdigest()!=entry['clean_sha256']:raise ValueError('Prior candidate was generated from a different clean reference.')
        initial_paths.append(args.initial_dir/entry['candidate'])
results=protect_batch(sources,destinations,steps=args.steps,epsilon=args.epsilon_levels/255,seed=42,progress=lambda p:print(json.dumps(p),flush=True),initial_paths=initial_paths)
for record,result,source,destination in zip(records,results,sources,destinations):
    result['quality']=measure(source,destination,args.epsilon_levels/255)
    record.update(quality=result['quality'],candidate_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),clean_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    destination.with_suffix('.json').write_text(json.dumps(result,indent=2))
manifest=dict(date='2026-10-29',status='experimental_frontier_effectiveness_not_tested',method='reduced MIRAGE-informed single-CLIP text-only surrogate',full_paper_reproduction=False,frontier_efficacy=None,steps=args.steps,epsilon_rgb=args.epsilon_levels/255,images=records,testing='User chooses arbitrary prompts and exact frontier models; no prompts are required by this protection pipeline.')
if args.initial_dir:manifest['prior_attempt']=dict(path=str(args.initial_dir),steps=prior['steps'],epsilon_rgb=prior['epsilon_rgb'],purpose='quality-budget refinement; original diagnostics retained')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
if any(record['quality']['gate']!='passed' for record in records):
    print('QUALITY REJECTION: no download-ready kit was published. Raw diagnostics retained.',flush=True)
    sys.exit(2)
(out/'README.txt').write_text('ImageShield experimental frontier test kit - 29 October 2026\n\nUse the three *protected-EXPERIMENTAL.png files directly in your chosen frontier image editor. Use ANY prompts you want. The clean-references folder provides matched comparison inputs.\n\nThese candidates passed local source-image fidelity checks. Protection/refusal against GPT Image 2, Nano Banana Pro, or any other frontier editor is NOT verified. The method is a reduced single-CLIP research implementation, NOT full MIRAGE. It omits the unpublished target images and seven ensemble members.\n\nFor useful feedback, record the exact editor/model, the prompt, which input file was uploaded, and the resulting image or refusal. If comparing, use the same prompt on the clean reference in a separate fresh conversation. Do not confuse generation errors with protection.\n\nExact settings, limitations, hashes and quality measurements are in manifest.json and the per-image JSON files. No images were sent to external inference by this pipeline.\n',encoding='utf-8')
cards=[]
for record in records:
    cards.append('<section><h2>'+html.escape(record['label'])+'</h2><img src="'+record['candidate']+'" alt="Experimental protection candidate"><p><a download href="'+record['candidate']+'">Download experimental PNG</a> · <a href="'+record['clean_reference']+'">Clean reference</a></p><p>Quality passed. Frontier effectiveness: untested.</p></section>')
(out/'index.html').write_text('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Frontier test kit</title><style>body{font:18px system-ui;background:#141922;color:#edf2f8;max-width:1100px;margin:auto;padding:24px}a{color:#9dd1ff}img{max-width:100%;max-height:700px}section{border-top:1px solid #596777;padding:24px 0}</style><h1>Three experimental images for your frontier tests</h1><p>Use any prompts in your chosen frontier image editor. All three files pass source fidelity. Protection effectiveness is unverified; this is a reduced research implementation.</p>'+''.join(cards),encoding='utf-8')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for path in out.rglob('*'):
        if path.is_file():z.write(path,path.relative_to(out))
if args.publish_downloads:
    if downloads.exists() or download_archive.exists():raise FileExistsError('Refusing to overwrite an existing frontier test kit: '+str(downloads))
    shutil.copytree(out,downloads);shutil.copy2(archive,download_archive)
    print('Download-ready kit: '+str(downloads),flush=True)
print(json.dumps(manifest),flush=True)
