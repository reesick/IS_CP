"""Explicit local research entry point. Never downloads weights or accepts gates."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from backend.app.ml.cad import preflight,protect
parser=argparse.ArgumentParser(description='Paper-derived CaD FLUX-Kontext research adapter; frontier efficacy unverified.')
parser.add_argument('--preflight',action='store_true')
parser.add_argument('--model-path',type=Path)
parser.add_argument('--input',type=Path)
parser.add_argument('--output',type=Path)
parser.add_argument('--steps',type=int,default=1000)
args=parser.parse_args()
if args.preflight:
    print(json.dumps(preflight(args.model_path),indent=2));sys.exit(0)
if not args.input or not args.output:parser.error('--input and --output are required for an actual run')
result=protect(args.input,args.output,args.model_path,steps=args.steps,progress=lambda p:print(json.dumps(p),flush=True))
args.output.with_suffix('.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
