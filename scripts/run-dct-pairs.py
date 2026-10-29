"""Actual paired local SD edits, including a real JPEG85 channel."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.ml.editor import edit_pair
out=ROOT/'outputs/research-2026-10-28/dct-shield'
base=ROOT/'outputs/dnew-tests/2026-10-28/03'
result=json.loads((out/'results.json').read_text())
for channel in ('local_png','jpeg_simulation'):
    result['paired_'+channel]=edit_pair(base/'clean.png',out/'EXPERIMENTAL-unverified-shorts.png',base/'edit-mask.png',out/channel,dict(prompt='A person wearing olive green shorts, a white shirt, white socks and black shoes, red background, realistic fashion photograph',seeds=[11,22,33],channel=channel),lambda done,total,stage:print(json.dumps(dict(done=done,total=total,stage=stage)),flush=True))
    (out/'results.json').write_text(json.dumps(result,indent=2,default=str))
print('Completed actual paired diagnostics; human efficacy review remains separate.',flush=True)
