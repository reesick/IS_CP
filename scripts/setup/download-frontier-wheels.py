"""Select official Windows wheels from the PyTorch index and verify its SHA256."""
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import requests
ROOT=Path(__file__).resolve().parents[2]
records=[]
for name,version in [('torch','2.6.0'),('torchvision','0.21.0')]:
    index=f'https://download.pytorch.org/whl/cu124/{name}/'
    response=requests.get(index,timeout=45);response.raise_for_status()
    pattern=rf'href="([^"]*{name}-{re.escape(version)}%2Bcu124-cp311-cp311-win_amd64\.whl#sha256=([a-f0-9]+))"'
    match=re.search(pattern,response.text,re.I)
    if not match:raise RuntimeError('Official index did not list the required Windows wheel: '+name)
    url=html.unescape(match.group(1));expected=match.group(2)
    if url.startswith('/'):url='https://download.pytorch.org'+url
    url=url.split('#')[0]
    target=ROOT/f'.cache/{name}-{version}+cu124-cp311-cp311-win_amd64.whl'
    if not target.exists():
        subprocess.run([sys.executable,str(ROOT/'scripts/setup/download_range.py'),url,str(target),'--workers','12'],check=True)
    with target.open('rb') as handle:actual=hashlib.file_digest(handle,'sha256').hexdigest()
    if actual!=expected:raise RuntimeError('Official wheel hash mismatch: '+name)
    records.append(dict(package=name,version=version+'+cu124',source=url,sha256=actual,bytes=target.stat().st_size))
    (ROOT/'docs/research/FRONTIER_WHEELS.json').write_text(json.dumps(records,indent=2))
    print('Official SHA256 matched: '+target.name,flush=True)
