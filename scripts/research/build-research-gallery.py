"""Rebuild a private local evidence gallery from actual completed artifacts."""
import html
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'outputs/research-2026-10-28';out.mkdir(parents=True,exist_ok=True)
def figure(path,label):
    path=Path(path)
    if not path.exists():return ''
    rel=Path(__import__('os').path.relpath(path,out)).as_posix()
    return f'<figure><a href="{html.escape(rel)}"><img loading="lazy" src="{html.escape(rel)}" alt="{html.escape(label)}"></a><figcaption>{html.escape(label)}</figcaption></figure>'
def table(metrics):
    return '<dl>'+''.join(f'<dt>{html.escape(str(k))}</dt><dd>{html.escape(str(v))}</dd>' for k,v in metrics.items())+'</dl>'
sections=[]
pg=out/'paper-baselines/results.json'
if pg.exists():
    data=json.loads(pg.read_text())
    for method in ('photoguard','diffvax_eval','diffvax_upstream_train'):
        paired=data.get(method+'_paired',{})
        rows=[]
        for pair in paired.get('pairs',[]):
            rows.append('<h3>Seed '+str(pair['seed'])+'</h3><div class="grid">'+''.join(figure(pair[k],label) for k,label in [('clean_input','Clean source'),('protected_input','Research candidate'),('edit_clean','Edit from clean source'),('edit_protected','Edit from candidate')])+'</div><p>Safety filtered: '+str(pair.get('safety_filtered'))+'. Human efficacy rating: not assigned.</p>')
        quality=data.get('photoguard_quality') if method=='photoguard' else None
        if method.startswith('diffvax'):
            records=json.loads((out/'diffvax/results.json').read_text())
            mode='eval' if method=='diffvax_eval' else 'upstream_train'
            quality=next(r['quality'] for r in records if r['image']==2 and r['bn_mode']==mode)
        sections.append('<section><h2>'+method+'</h2><p>Local SD1.5 inpainting transfer diagnostic, three matched seeds. Prompt: '+html.escape(paired.get('prompt',''))+'. No frontier inference.</p>'+(table(quality) if quality else '')+''.join(rows)+'</section>')
for folder,filename,title in [('contrastive-probe','results-native.json','Reduced refusal-surrogate probe: 5,000 steps'),('dct-shield','results.json','DCT-Shield base paper reimplementation')]:
    path=out/folder/filename
    if not path.exists():continue
    data=json.loads(path.read_text())
    quality=data.get('quality')
    if not isinstance(quality,dict):quality=data.get('product_quality_diagnostic',{})
    source=out/'contrastive-probe/clean-native.png' if folder=='contrastive-probe' else ROOT/'outputs/dnew-tests/2026-10-28/03/clean.png'
    candidate=out/folder/('EXPERIMENTAL-unverified-shorts-native.png' if folder=='contrastive-probe' else 'EXPERIMENTAL-unverified-shorts.png')
    sections.append('<section><h2>'+title+'</h2><p class="bad">Experimental. Protection effectiveness has not been established. Quality gate: '+html.escape(str(quality.get('gate','unknown')))+'.</p>'+table(quality)+'<div class="grid">'+figure(source,'Clean source')+figure(candidate,'Experimental candidate')+'</div><p><a href="'+folder+'/'+filename+'">Exact parameters and raw results</a></p></section>')
    for channel in ('local_png','jpeg_simulation'):
        paired=data.get('paired_'+channel)
        if not paired:continue
        rows=[]
        for pair in paired.get('pairs',[]):
            rows.append('<h3>Seed '+str(pair['seed'])+'</h3><div class="grid">'+''.join(figure(pair[k],label) for k,label in [('clean_input','Actual channel input: clean'),('protected_input','Actual channel input: candidate'),('edit_clean','Edit from clean'),('edit_protected','Edit from candidate')])+'</div><p>Safety filtered: '+str(pair.get('safety_filtered'))+'. Human efficacy rating: not assigned.</p>')
        sections.append('<section><h2>'+title+': '+channel+'</h2><p>'+html.escape(paired.get('prompt',''))+'</p>'+''.join(rows)+'</section>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ImageShield local research evidence</title><style>body{font:16px/1.5 system-ui;background:#11151b;color:#e8edf3;max-width:1500px;margin:auto;padding:24px}a{color:#8ecaff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}figure{margin:0}img{width:100%;max-height:650px;object-fit:contain;background:#242b33}figcaption{padding:8px}section{border-top:1px solid #465262;margin-top:32px;padding-top:16px}.bad{color:#ffbb9d}dl{display:grid;grid-template-columns:minmax(160px,1fr) 2fr;max-width:750px}dt,dd{margin:0;padding:3px}h1{line-height:1.2}</style><h1>ImageShield: actual local research results</h1><p>28 October 2026. Private files stay local. This gallery shows completed experiments, including failures. It is not an effective-protection certification.</p><p class="bad">No current result establishes protection against GPT Image 2 or Nano Banana Pro. Surrogate score, output differences and successful execution are not edit-prevention rates.</p>'''+''.join(sections)+'</html>'
(out/'index.html').write_text(page,encoding='utf-8')
print(out/'index.html')
