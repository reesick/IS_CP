"""Explicit, resumable SD1.5 download; no API import triggers a network call."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('HF_HOME', str(ROOT / '.cache' / 'huggingface'))
REGISTRY = ROOT / 'model-registry.json'
REPO = 'stable-diffusion-v1-5/stable-diffusion-inpainting'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=['sd15_inpaint'], required=True)
    parser.add_argument('--revision', default='main')
    parser.add_argument('--ranged', action='store_true', help='Use resumable parallel byte ranges for large weights on slow links')
    parser.add_argument('--workers', type=int, choices=range(1, 17), default=6)
    args = parser.parse_args()
    from huggingface_hub import HfApi, snapshot_download, hf_hub_url
    api = HfApi()
    info = api.model_info(REPO, revision=args.revision, files_metadata=True)
    revision = info.sha
    files = {f.rfilename: f.size or 0 for f in info.siblings}
    expected_hashes = {f.rfilename: getattr(f.lfs, 'sha256', None) for f in info.siblings if f.lfs}
    selected = [p for p in files if p.endswith(('.json', '.txt', '.md')) and '/' not in p or p.endswith(('/config.json', '/scheduler_config.json', '/tokenizer_config.json', '/special_tokens_map.json', '/vocab.json', '/merges.txt', '/preprocessor_config.json'))]
    selected = list(set(selected + ['model_index.json']))
    fp16 = all(any(p.startswith(component + '/') and p.endswith('.fp16.safetensors') for p in files) for component in ['unet', 'vae', 'text_encoder'])
    for component in ['unet', 'vae', 'text_encoder', 'safety_checker']:
        candidates = [p for p in files if p.startswith(component + '/') and p.endswith('.safetensors') and ('.fp16.' in p if fp16 else '.fp16.' not in p)]
        if not candidates:
            raise RuntimeError(f'No safe compatible weights found for {component}; refusing pickle fallback')
        selected.append(sorted(candidates)[0])
    needed = sum(files.get(p, 0) for p in selected)
    destination = ROOT / 'models' / args.model
    destination.mkdir(parents=True, exist_ok=True)
    existing = sum((destination / p).stat().st_size for p in selected if (destination / p).exists())
    required_free = max(0, needed - existing) + 2 * 1024**3
    if shutil.disk_usage(ROOT).free < required_free:
        raise RuntimeError(f'Insufficient disk: need {required_free / 1024**3:.1f} GiB free')
    registry = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else json.loads((ROOT / 'models.example.json').read_text())
    model = next(m for m in registry['models'] if m['id'] == args.model)
    model.update(revision=revision, local_path=str(destination), snapshot_path=str(destination), ready=False, weights_ready=False, status='downloading', variant='fp16' if fp16 else None)
    REGISTRY.write_text(json.dumps(registry, indent=2))
    print(json.dumps({'repo': REPO, 'revision': revision, 'bytes': needed, 'variant': model['variant']}), flush=True)
    try:
        small = selected
        if args.ranged:
            large = [p for p in selected if files.get(p, 0) > 64 * 1024**2]
            small = [p for p in selected if p not in large]
            snapshot_download(REPO, revision=revision, local_dir=destination, allow_patterns=small, max_workers=2)
            for name in large:
                target = destination / name
                if target.exists() and target.stat().st_size == files[name]:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run([sys.executable, str(ROOT / 'scripts' / 'download_range.py'), hf_hub_url(REPO, name, revision=revision), str(target), '--workers', str(args.workers)], check=True)
        else:
            snapshot_download(REPO, revision=revision, local_dir=destination, allow_patterns=selected, max_workers=2)
        hashes = {}
        for name in selected:
            file = destination / name
            if not file.is_file() or (files.get(name) and file.stat().st_size != files[name]):
                raise RuntimeError('Downloaded snapshot is incomplete')
            digest = hashlib.sha256()
            with file.open('rb') as handle:
                for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b''):
                    digest.update(chunk)
            actual_hash = digest.hexdigest()
            expected_hash = expected_hashes.get(name)
            if expected_hash and actual_hash != expected_hash:
                raise RuntimeError(f'Download hash mismatch for {name}')
            hashes[name] = {'sha256': actual_hash, 'bytes': file.stat().st_size, 'lfs_sha256_verified': bool(expected_hash)}
        model.update(status='downloaded_not_runtime_validated', weights_ready=True, files=hashes)
        registry['status'] = 'downloaded_not_runtime_validated'
        REGISTRY.write_text(json.dumps(registry, indent=2))
        print('Sizes checked and available Hugging Face LFS SHA256 hashes matched; runtime validation still required.', flush=True)
    except Exception:
        model.update(status='download_failed', ready=False, weights_ready=False)
        REGISTRY.write_text(json.dumps(registry, indent=2))
        raise

if __name__ == '__main__':
    main()
