"""Explicit download of the paper-listed public CLIP surrogate, pinned/hash checked."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from huggingface_hub import HfApi,snapshot_download,hf_hub_url

ROOT=Path(__file__).resolve().parents[2]
repo='laion/CLIP-ViT-B-32-laion2B-s34B-b79K'
revision='1a25a446712ba5ee05982a381eed697ef9b435cf'
target=ROOT/'models/research-clip-b32'
target.mkdir(parents=True,exist_ok=True)
info=HfApi().model_info(repo,revision=revision,files_metadata=True)
small=['config.json','preprocessor_config.json','tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','special_tokens_map.json','README.md']
snapshot_download(repo,revision=revision,local_dir=target,allow_patterns=small,max_workers=4)
weight=next(f for f in info.siblings if f.rfilename=='model.safetensors')
path=target/'model.safetensors'
if not path.exists() or path.stat().st_size!=weight.size:
    subprocess.run([sys.executable,str(ROOT/'scripts/setup/download_range.py'),hf_hub_url(repo,'model.safetensors',revision=revision),str(path),'--workers','8'],check=True)
actual=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
expected=weight.lfs['sha256']
if actual!=expected:
    raise RuntimeError('Encoder weight hash mismatch.')
record=dict(repo_id=repo,revision=revision,sha256=actual,license='MIT',local_path=str(target.relative_to(ROOT)),purpose='paper-listed surrogate, not a reproduced MIRAGE efficacy result')
(target/'imageshield-provenance.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record),flush=True)
