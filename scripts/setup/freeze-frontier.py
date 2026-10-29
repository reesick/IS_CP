"""Write portable installed pins and keep verified wheel origins separate."""
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
lines=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines()
versions={name:metadata.version(name) for name in ('torch','torchvision','diffusers','transformers','accelerate')}
for name in ('torch','torchvision'):
    lines=[f'{name}=={versions[name]}' if line.startswith(name+' @ ') else line for line in lines]
(ROOT/'requirements-frontier.lock').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/'docs/research/FRONTIER_ENVIRONMENT.json').write_text(json.dumps(dict(python=platform.python_version(),packages=versions,wheel_hashes='FRONTIER_WHEELS.json',purpose='separate research architecture validation; no pretrained frontier defense execution implied'),indent=2))
print(json.dumps(versions))
