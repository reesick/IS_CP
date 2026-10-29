import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.app.ml.contrastive_probe import protect
from backend.app.services.metrics import measure
parser=argparse.ArgumentParser(description='Local exploratory surrogate probe; NOT full MIRAGE or verified refusal.')
parser.add_argument('--steps',type=int,default=250)
parser.add_argument('--native',action='store_true')
args=parser.parse_args()
out=ROOT/'outputs/research-2026-10-28/contrastive-probe'
out.mkdir(parents=True,exist_ok=True)
source=ROOT/'outputs/dnew-tests/2026-10-28/03/clean.png'
suffix='-native' if args.native else ''
if args.native:
    from PIL import Image,ImageOps
    samples=json.loads((ROOT/'data/dnew-tests/samples.json').read_text())
    image=ImageOps.exif_transpose(Image.open(samples[2]['path'])).convert('RGB')
    original_size=list(image.size)
    image.thumbnail((1024,1024),Image.Resampling.LANCZOS)
    source=out/'clean-native.png';image.save(source)
destination=out/f'EXPERIMENTAL-unverified-shorts{suffix}.png'
result=protect(source,destination,steps=args.steps,epsilon=8/255,progress=lambda p:print(json.dumps(p),flush=True))
result['quality']=measure(source,destination,8/255)
if args.native:result['source_original_size']=original_size
(out/f'results{suffix}.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='history'}),flush=True)
