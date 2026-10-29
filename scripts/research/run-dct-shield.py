import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from backend.app.ml.dct_shield import protect
from backend.app.services.metrics import measure
parser=argparse.ArgumentParser(description='Experimental DCT-Shield base reimplementation; efficacy unknown.')
parser.add_argument('--steps',type=int,default=1000)
args=parser.parse_args()
out=ROOT/'outputs/research-2026-10-28/dct-shield';out.mkdir(parents=True,exist_ok=True)
source=ROOT/'outputs/dnew-tests/2026-10-28/03/clean.png'
dest=out/'EXPERIMENTAL-unverified-shorts.png'
result=protect(source,dest,steps=args.steps,progress=lambda p:print(json.dumps(p),flush=True))
# No coefficient budget is mislabeled as an RGB budget. This records the usual
# product RGB gate separately as a compatibility diagnostic.
result['product_quality_diagnostic']=measure(source,dest,8/255)
(out/'results.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='history'}),flush=True)
