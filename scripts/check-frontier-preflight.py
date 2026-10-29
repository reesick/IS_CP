import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.ml.cad import preflight
result=preflight()
(ROOT/'docs/research/FRONTIER_PREFLIGHT.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
