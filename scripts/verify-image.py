"""Identify any image against the ImageShield evidence registry (CLI).

Usage:  .venv\\Scripts\\python.exe scripts\\verify-image.py path\\to\\image.png [more files]
        .venv\\Scripts\\python.exe scripts\\verify-image.py --chain     (check the audit log)

Every check is appended to the hash-chained audit log in outputs/integrity/.
Open the dashboard once first so the registry is built.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import audit  # noqa: E402

COLORS = {'VERIFIED': '32', 'MODIFIED': '33', 'TAMPERED': '31', 'UNKNOWN': '36', 'INVALID': '31'}


def main(args):
    if not args:
        print(__doc__)
        return 2
    if args == ['--chain']:
        chain = audit.verify_chain()
        print(('CHAIN INTACT' if chain['ok'] else f'CHAIN BROKEN at line {chain["broken_at"]}: {chain.get("reason")}') + f'  ({chain["count"]} entries, head {chain["head"][:16]})')
        return 0 if chain['ok'] else 1
    if not audit.load_registry():
        print('Registry is empty. Start the dashboard once (scripts/start-visible.ps1) so it registers the samples.')
        return 2
    worst = 0
    for raw in args:
        path = Path(raw)
        if not path.is_file():
            print(f'[MISSING ] {raw}')
            worst = 1
            continue
        r = audit.identify(path.read_bytes(), path.name, 'cli')
        tag = f'\033[{COLORS.get(r["verdict"], "0")}m[{r["verdict"]:<8}]\033[0m'
        print(f'{tag} {path.name}: {r["summary"]}')
        print(f'           sha256 {r["sha256"]}')
        if r.get('similarity') is not None:
            extra = f', {r["pixels_changed"]}% pixels changed' if r.get('pixels_changed') is not None else ''
            print(f'           similarity {r["similarity"]}%{extra}; protection present: {r["protection_present"]}')
        print(f'           audit entry #{r["audit_seq"]} {r["audit_hash"][:16]}')
        worst = max(worst, 0 if r['verdict'] == 'VERIFIED' else 1)
    return worst


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
