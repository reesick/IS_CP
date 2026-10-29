"""Freeze installed versions portably, retaining local wheel hashes separately."""
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

root=Path(__file__).resolve().parents[2]
frozen=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines()
provenance={}
for package in ('torch','torchvision'):
    dist=metadata.distribution(package)
    direct=dist.read_text('direct_url.json')
    provenance[package]=dict(version=dist.version,installed_wheel=json.loads(direct) if direct else None)
    frozen=[f'{package}=={dist.version}' if line.startswith(package+' @ ') else line for line in frozen]
(root/'requirements-ml.lock').write_text('\n'.join(frozen)+'\n',encoding='utf-8')
(root/'docs/ML_ENVIRONMENT.json').write_text(json.dumps(dict(python=platform.python_version(),platform=platform.platform(),packages=provenance),indent=2),encoding='utf-8')
print('Installed ML versions pinned; local CUDA wheel hashes recorded separately.')
