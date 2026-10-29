"""ImageShield evidence registry and tamper-evident audit trail.

* Registry: every pipeline image (source photo, clean original, protected
  export, AI edit of each) is recorded with its SHA-256 and a 256-bit
  perceptual difference hash (dHash).
* identify(): exact SHA-256 match first; otherwise perceptual matching finds
  re-encoded, resized, screenshotted or edited copies, then a pixel
  comparison decides between near-identical candidates (original vs protected).
* Audit log: append-only JSON lines. Each entry stores the previous entry's
  hash and its own SHA-256 over its canonical JSON (a hash chain), so editing,
  deleting or reordering any past entry is detectable by verify_chain().
  Uploaded images are never stored, only their hash and the verdict.
"""
from __future__ import annotations

import hashlib
import io
import json
import threading
import time
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = 20_000_000
ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'outputs' / 'integrity'
LOG = DIR / 'audit-log.jsonl'
REGISTRY = DIR / 'registry.json'
GENESIS = '0' * 64
PAD = np.array([244, 244, 245], dtype=np.int16)
_lock = threading.Lock()

ROLE_LABELS = {
    'source': 'Source photo (before the pipeline)',
    'original': 'Clean original (512 x 512 reference)',
    'protected': 'ImageShield-protected export',
    'edit_original': 'AI edit of the unprotected original',
    'edit_protected': 'AI-tampered copy of the protected image',
    'jpeg_edit_original': 'AI edit of the original after JPEG-85',
    'jpeg_edit_protected': 'AI edit of the protected image after JPEG-85',
}
STRONG, WEAK = 40, 64  # Hamming distance out of 256 bits


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _dhash(img: Image.Image, size: int = 16) -> np.ndarray:
    gray = np.asarray(img.convert('L').resize((size + 1, size), Image.Resampling.LANCZOS), dtype=np.int16)
    return (gray[:, 1:] > gray[:, :-1]).flatten()


def _hex(bits: np.ndarray) -> str:
    return np.packbits(bits.astype(np.uint8)).tobytes().hex()


def _bits(hexstr: str) -> np.ndarray:
    return np.unpackbits(np.frombuffer(bytes.fromhex(hexstr), dtype=np.uint8)).astype(bool)


def _content_box(img: Image.Image):
    """Bounding box of non-letterbox pixels (the app pads with #f4f4f5)."""
    arr = np.asarray(img.convert('RGB'), dtype=np.int16)
    mask = (np.abs(arr - PAD) > 12).any(axis=2)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    w, h = img.size
    return None if (box[2] - box[0]) * (box[3] - box[1]) > 0.97 * w * h else box


def _hashes(img: Image.Image, box=None):
    out = {'full': _hex(_dhash(img))}
    box = box or _content_box(img)
    if box:
        out['crop'] = _hex(_dhash(img.crop(box)))
        out['box'] = list(box)
    return out


# ---------------- audit log (hash chain) ----------------

def _canon(entry: dict) -> str:
    return json.dumps(entry, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _last():
    if not LOG.is_file():
        return 0, GENESIS
    last = None
    with LOG.open('r', encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                last = line
    if not last:
        return 0, GENESIS
    entry = json.loads(last)
    return entry['seq'], entry['entry_hash']


def append(event: dict) -> dict:
    with _lock:
        DIR.mkdir(parents=True, exist_ok=True)
        seq, prev = _last()
        entry = {'seq': seq + 1, 'time': time.strftime('%Y-%m-%dT%H:%M:%S%z'), **event, 'prev_hash': prev}
        entry['entry_hash'] = sha256_bytes(_canon(entry).encode())
        with LOG.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + '\n')
        return entry


def read_log(limit: int = 200):
    if not LOG.is_file():
        return []
    lines = [l for l in LOG.read_text(encoding='utf-8').splitlines() if l.strip()]
    return [json.loads(l) for l in lines[-limit:]][::-1]


def verify_chain() -> dict:
    """Recompute every entry hash and link. Any edit, deletion or reorder breaks it."""
    if not LOG.is_file():
        return {'ok': True, 'count': 0, 'broken_at': None, 'head': GENESIS}
    prev, count = GENESIS, 0
    for number, line in enumerate(LOG.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            return {'ok': False, 'count': count, 'broken_at': number, 'reason': 'unreadable entry', 'head': prev}
        claimed = entry.pop('entry_hash', None)
        if entry.get('prev_hash') != prev or sha256_bytes(_canon(entry).encode()) != claimed or entry.get('seq') != count + 1:
            return {'ok': False, 'count': count, 'broken_at': number, 'reason': 'hash mismatch: entry edited, removed or reordered', 'head': prev}
        prev, count = claimed, count + 1
    return {'ok': True, 'count': count, 'broken_at': None, 'head': prev}


# ---------------- registry ----------------

def load_registry() -> dict:
    try:
        return json.loads(REGISTRY.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def register_sample(case: str, label: str, files: dict) -> dict:
    """files: role -> path. Logs a REGISTER event only when the hash set changes."""
    with _lock:
        registry = load_registry()
    clean = files.get('original')
    box = None
    if clean and Path(clean).is_file():
        with Image.open(clean) as opened:
            box = _content_box(opened.convert('RGB'))
    items = []
    for role, path in files.items():
        if not path or not Path(path).is_file():
            continue
        with Image.open(path) as opened:
            img = opened.convert('RGB')
            hashes = _hashes(img, box if role != 'source' else None)
            size = list(img.size)
        items.append({'sample': case, 'label': label, 'role': role, 'role_label': ROLE_LABELS.get(role, role),
                      'file': str(Path(path).resolve()), 'sha256': sha256_file(path), 'bytes': Path(path).stat().st_size,
                      'size': size, 'dhash': hashes})
    previous = {i['role']: i['sha256'] for i in registry.get(case, {}).get('items', [])}
    current = {i['role']: i['sha256'] for i in items}
    record = {'sample': case, 'label': label, 'items': items,
              'registered_at': registry.get(case, {}).get('registered_at') if previous == current else time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    with _lock:
        registry = load_registry()
        registry[case] = record
        DIR.mkdir(parents=True, exist_ok=True)
        REGISTRY.write_text(json.dumps(registry, indent=1), encoding='utf-8')
    if previous != current:
        append({'action': 'REGISTER', 'sample': case, 'label': label,
                'files': {i['role']: i['sha256'] for i in items}})
    return record


def _all_items():
    return [item for rec in load_registry().values() for item in rec.get('items', [])]


def identify(data: bytes, filename: str = 'upload', source: str = 'dashboard') -> dict:
    """Identify an image against the registry and append a VERIFY entry."""
    digest = sha256_bytes(data)
    items = _all_items()
    result = {'filename': Path(filename).name[:120], 'sha256': digest, 'bytes': len(data), 'metadata': inspect_metadata(data)}
    exact = next((i for i in items if i['sha256'] == digest), None)
    if exact:
        tampered = exact['role'] in ('edit_protected', 'jpeg_edit_protected')
        result.update(verdict='TAMPERED' if tampered else 'VERIFIED', exact=True, match=_public(exact), similarity=100.0, pixels_changed=0.0,
                      summary=(f'Exact match: {exact["role_label"]} of "{exact["label"]}". '
                               + ('This is an AI-edited copy of a protected image.' if tampered else 'The file is untouched.')))
    else:
        try:
            with Image.open(io.BytesIO(data)) as opened:
                opened.load()
                img = opened.convert('RGB')
        except Exception:
            result.update(verdict='INVALID', summary='Not a readable image file.')
            img = None
        if img is not None:
            result['size'] = list(img.size)
            probe = _hashes(img)
            scored = []
            for item in items:
                pairs = [(probe['full'], item['dhash']['full'])]
                if 'crop' in item['dhash']:
                    pairs += [(probe['full'], item['dhash']['crop'])]
                if 'crop' in probe:
                    pairs += [(probe['crop'], item['dhash']['full'])]
                    if 'crop' in item['dhash']:
                        pairs += [(probe['crop'], item['dhash']['crop'])]
                dist = min(int((_bits(a) ^ _bits(b)).sum()) for a, b in pairs)
                scored.append((dist, item))
            scored.sort(key=lambda pair: pair[0])
            if not scored or scored[0][0] > WEAK:
                result.update(verdict='UNKNOWN', similarity=round(100 * (1 - scored[0][0] / 256), 1) if scored else None,
                              summary='No match. This image did not come from the ImageShield pipeline.')
            else:
                best_d = scored[0][0]
                near = [it for d, it in scored if d <= best_d + 6]
                ranked = sorted(near, key=lambda it: _pixel_gap(img, it))
                best = ranked[0]
                signal = None
                if best['role'] in ('original', 'protected'):
                    pair = {i['role']: i for i in items if i['sample'] == best['sample'] and i['role'] in ('original', 'protected')}
                    if len(pair) == 2:
                        signal = _which_of_pair(img, pair['original'], pair['protected'])
                        if signal is not None:
                            best = pair['protected'] if signal > 0 else pair['original']
                result['protection_signal'] = None if signal is None else round(signal, 3)
                gap = _pixel_gap(img, best)
                changed = _changed_pct(img, best)
                dist = next(d for d, it in scored if it is best)
                similarity = round(100 * (1 - dist / 256), 1)
                base = best['role']
                if base in ('edit_protected', 'jpeg_edit_protected', 'edit_original', 'jpeg_edit_original'):
                    verdict = 'TAMPERED'
                else:
                    verdict = 'MODIFIED'
                how = 'same size, pixels changed' if changed is not None else 'resized, cropped or re-encoded'
                result.update(verdict=verdict, match=_public(best), similarity=similarity, pixels_changed=changed,
                              mean_difference=round(gap, 2), confidence='high' if dist <= STRONG else 'medium',
                              exact=False, summary=f'Not byte-identical, but derived from "{best["label"]}": {best["role_label"]} ({how}).')
    if result.get('match'):
        rec = load_registry().get(result['match']['sample'], {})
        result['registered_at'] = rec.get('registered_at')
    result['protection_present'] = bool(result.get('match') and result['match']['role'] in ('protected', 'edit_protected', 'jpeg_edit_protected'))
    entry = append({'action': 'VERIFY', 'source': source, 'filename': result['filename'], 'sha256': digest,
                    'verdict': result['verdict'], 'matched': (result.get('match') or {}).get('ref'),
                    'similarity': result.get('similarity')})
    result['audit_seq'] = entry['seq']
    result['audit_hash'] = entry['entry_hash']
    return result


def inspect_metadata(data: bytes) -> dict:
    """What the file's own metadata claims. Shown for contrast: metadata can be stripped, our proof cannot."""
    info = {'format': None, 'exif': False, 'c2pa': False, 'claims': []}
    try:
        with Image.open(io.BytesIO(data)) as opened:
            info['format'] = opened.format
            info['exif'] = bool(opened.getexif())
            info['text_chunks'] = sorted(k for k in getattr(opened, 'text', {}) or {})[:8]
    except Exception:
        pass
    head = data[:4_000_000]
    info['c2pa'] = b'c2pa' in head or b'jumb' in head
    for needle, name in ((b'OpenAI', 'OpenAI'), (b'ChatGPT', 'ChatGPT'), (b'DALL', 'DALL-E'), (b'Google', 'Google'), (b'Gemini', 'Gemini'),
                         (b'Adobe', 'Adobe'), (b'Firefly', 'Firefly'), (b'Midjourney', 'Midjourney'), (b'Stable Diffusion', 'Stable Diffusion'), (b'ComfyUI', 'ComfyUI')):
        if needle in head:
            info['claims'].append(name)
    info['ai_generator_claimed'] = bool(info['claims'])
    return info


def _public(item):
    return {'sample': item['sample'], 'label': item['label'], 'role': item['role'], 'role_label': item['role_label'],
            'sha256': item['sha256'], 'ref': f'{item["sample"]}/{item["role"]}'}


def _load(item):
    with Image.open(item['file']) as opened:
        return opened.convert('RGB')


def _pixel_gap(img, item) -> float:
    """Mean absolute difference (0-255) after resizing the probe to the record's size."""
    try:
        ref = np.asarray(_load(item), dtype=np.int16)
    except Exception:
        return 1e9
    probe = np.asarray(img.resize((ref.shape[1], ref.shape[0]), Image.Resampling.BILINEAR), dtype=np.int16)
    return float(np.abs(ref - probe).mean())


def _degrade(ref, size, quality, resample=Image.Resampling.BILINEAR):
    x = ref.resize(size, resample) if ref.size != size else ref
    if quality:
        buf = io.BytesIO()
        x.save(buf, 'JPEG', quality=quality)
        buf.seek(0)
        x = Image.open(buf).convert('RGB')
    return np.asarray(x, dtype=np.float32)


def _which_of_pair(img, original, protected):
    """Replay likely degradations (resize + JPEG 95..45) on both references.
    Returns the relative MSE advantage of 'protected' (>0 means the probe is a protected copy)."""
    try:
        o, p = _load(original), _load(protected)
    except Exception:
        return None
    probe = np.asarray(img, dtype=np.float32)
    def best(ref):
        filters = (Image.Resampling.BILINEAR, Image.Resampling.BICUBIC, Image.Resampling.LANCZOS) if ref.size != img.size else (Image.Resampling.BILINEAR,)
        return min(float(((_degrade(ref, img.size, q, f) - probe) ** 2).mean()) for q in (None, 95, 90, 85, 75, 60, 45) for f in filters)
    mo, mp = best(o), best(p)
    return (mo - mp) / max(mo, mp, 1e-6)


def _protection_signal(img, original, protected):
    """Correlation between (probe - original) and the known perturbation (protected - original).
    Survives JPEG and mild resizing; near 0 for the clean original, high for protected copies."""
    try:
        o = np.asarray(_load(original), dtype=np.float32)
        p = np.asarray(_load(protected), dtype=np.float32)
    except Exception:
        return None
    if o.shape != p.shape:
        return None
    probe = np.asarray(img.resize((o.shape[1], o.shape[0]), Image.Resampling.BILINEAR), dtype=np.float32)
    delta = (p - o).ravel()
    resid = (probe - o).ravel()
    denom = float(np.linalg.norm(delta) * np.linalg.norm(resid))
    return float(resid @ delta / denom) if denom else 0.0


def _changed_pct(img, item):
    if list(img.size) != item['size']:
        return None
    ref = np.asarray(_load(item), dtype=np.int16)
    probe = np.asarray(img, dtype=np.int16)
    return round(float((np.abs(ref - probe).max(axis=2) > 0).mean() * 100), 2)
