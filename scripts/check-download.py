"""Verify the exact protected PNG download from the completed local smoke."""
import hashlib
import io
import json
from pathlib import Path
import httpx
from PIL import Image

root=Path(__file__).resolve().parents[1]
evidence=json.loads((root/'docs/screenshots/gpu-browser-qa.json').read_text())
session=json.loads((root/'data/browser-smoke/session.json').read_text())
cookies={c['name']:c['value'] for c in session['cookies']}
artifact=evidence['protection']['output']['artifacts']['protected']
response=httpx.get('http://127.0.0.1:8000/api/v1/artifacts/'+artifact,cookies=cookies)
response.raise_for_status()
image=Image.open(io.BytesIO(response.content))
assert image.format=='PNG' and image.size==(512,512)
assert not image.getexif()
(root/'data/browser-smoke/download-protected.png').write_bytes(response.content)
result=dict(passed=True,status=response.status_code,bytes=len(response.content),dimensions=list(image.size),exif_removed=True,sha256=hashlib.sha256(response.content).hexdigest())
(root/'docs/screenshots/protected-download.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
