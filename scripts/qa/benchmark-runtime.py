"""Same-input timing of model reuse and UNet checkpoint recomputation."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.app.ml.defenders import protect

out=ROOT/'data/speed-benchmark'
out.mkdir(parents=True,exist_ok=True)
results=[]
for label,checkpoint in [('cold_checkpointed',True),('warm_checkpointed',True),('warm_vae_checkpoint_only',False)]:
    started=time.perf_counter()
    path=out/(label+'.png')
    try:
        provenance=protect(ROOT/'data/ml-smoke/clean.png',ROOT/'data/ml-smoke/mask.png',path,dict(profile='smoke',epsilon=1/255,seed=42,checkpoint_unet=checkpoint))
        record=dict(label=label,elapsed_seconds=time.perf_counter()-started,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),peak_cuda_allocated_bytes=provenance['peak_cuda_allocated_bytes'],passed=True)
    except Exception as exc:
        record=dict(label=label,elapsed_seconds=time.perf_counter()-started,passed=False,error_type=type(exc).__name__)
    results.append(record)
    (out/'results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(record),flush=True)
