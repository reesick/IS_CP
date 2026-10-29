"""Full published PhotoGuard encoder profile + real DiffVax paired diagnostics.

No efficacy inference is made from quality or edited-image distance.
"""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.ml.photoguard import protect
from backend.app.ml.editor import edit_pair
from backend.app.services.metrics import measure
out=ROOT/'outputs/research-2026-10-28/paper-baselines'
out.mkdir(parents=True,exist_ok=True)
base=ROOT/'outputs/dnew-tests/2026-10-28/02'
result=dict(purpose='Paper-baseline research diagnostics; not a product protection success')
def progress(done,total,stage):print(json.dumps(dict(stage=stage,done=done,total=total)),flush=True)
try:
    result['photoguard']=protect(base/'clean.png',base/'edit-mask.png',out/'photoguard.png',dict(seed=42),progress)
    result['photoguard_quality']=measure(base/'clean.png',out/'photoguard.png',.03)
    (out/'results.json').write_text(json.dumps(result,indent=2))
    for method,protected in [('photoguard',out/'photoguard.png'),('diffvax_eval',ROOT/'outputs/research-2026-10-28/diffvax/02-eval.png'),('diffvax_upstream_train',ROOT/'outputs/research-2026-10-28/diffvax/02-upstream_train.png')]:
        result[method+'_paired']=edit_pair(base/'clean.png',protected,base/'edit-mask.png',out/method,dict(prompt='An olive green baseball cap, embroidered front, realistic product photography',seeds=[11,22,33],channel='local_png'),progress)
        (out/'results.json').write_text(json.dumps(result,indent=2,default=str))
except Exception as exc:
    result['error']=dict(type=type(exc).__name__,message=str(exc))
    (out/'results.json').write_text(json.dumps(result,indent=2,default=str))
    raise
