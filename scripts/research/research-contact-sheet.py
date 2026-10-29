"""Contact sheet for visual QA; no pixel measurements use this resized view."""
import hashlib
import json
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
base=ROOT/'outputs/research-2026-10-28/paper-baselines'
methods=['photoguard','diffvax_eval','diffvax_upstream_train']
sheet=Image.new('RGB',(1200,990),'#171c24');draw=ImageDraw.Draw(sheet)
checks=[]
for row,seed in enumerate([11,22,33]):
    clean_paths=[base/m/f'{seed}_edit_clean.png' for m in methods]
    hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in clean_paths]
    checks.append(dict(seed=seed,matched_clean_outputs=len(set(hashes))==1,sha256=hashes))
    paths=[clean_paths[0]]+[base/m/f'{seed}_edit_protected.png' for m in methods]
    labels=['Clean baseline']+methods
    for col,(path,label) in enumerate(zip(paths,labels)):
        sheet.paste(Image.open(path).convert('RGB').resize((300,300)),(300*col,330*row+30))
        draw.text((300*col+5,330*row+8),f'{seed}: {label}',fill='white')
sheet.save(base/'contact-sheet.jpg',quality=94)
(base/'clean-baseline-hash-check.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks))
dct=ROOT/'outputs/research-2026-10-28/dct-shield'
if (dct/'results.json').exists():
    sheet=Image.new('RGB',(1200,990),'#171c24');draw=ImageDraw.Draw(sheet)
    for row,seed in enumerate([11,22,33]):
        variants=[(channel,kind) for channel in ('local_png','jpeg_simulation') for kind in ('clean','protected')]
        for col,(channel,kind) in enumerate(variants):
            path=dct/channel/f'{seed}_edit_{kind}.png'
            if not path.exists():continue
            sheet.paste(Image.open(path).convert('RGB').resize((300,300)),(col*300,row*330+30))
            draw.text((col*300+5,row*330+8),f'{seed}: {channel} {kind}',fill='white')
    sheet.save(dct/'contact-sheet.jpg',quality=94)
