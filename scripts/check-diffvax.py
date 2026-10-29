"""Measure released DiffVax exports in both BatchNorm modes before integration."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.ml.diffvax import protect
from backend.app.services.metrics import measure
out=ROOT/'outputs/research-2026-10-28/diffvax'
out.mkdir(parents=True,exist_ok=True)
results=[]
for index in (1,2,3):
    base=ROOT/f'outputs/dnew-tests/2026-10-28/{index:02d}'
    for mode in ('upstream_train','eval'):
        destination=out/f'{index:02d}-{mode}.png'
        try:
            provenance=protect(base/'clean.png',base/'edit-mask.png',destination,dict(bn_mode=mode))
            quality=measure(base/'clean.png',destination,1.0)
            quality['epsilon']=None
            quality['budget_reason']='Released checkpoint has no enforced perturbation budget.'
            results.append(dict(image=index,bn_mode=mode,quality=quality,provenance=provenance,export=str(destination.relative_to(ROOT))))
        except Exception as exc:
            results.append(dict(image=index,bn_mode=mode,error_type=type(exc).__name__,error=str(exc)))
        (out/'results.json').write_text(json.dumps(results,indent=2))
        print(json.dumps(results[-1]),flush=True)
