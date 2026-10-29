"""Checked UI state fixes; does not run models or reference scripts."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'frontend/research-demo/app.js'
s=p.read_text()
changes=[
 ('loaded = false, liveBusy = false, liveTimer;','loaded = false, liveBusy = false, liveTimer, latestResult = null;'),
 ('window.addEventListener("hashchange",()=>{showView();requestAnimationFrame(()=>window.scrollTo(0,0));});', 'window.addEventListener("hashchange",()=>{showView();const context=location.hash==="#playground"?preloaded:selected;if(context)$("#method").textContent=context.method;requestAnimationFrame(()=>window.scrollTo(0,0));});'),
 ('message("Sample preloaded",false,"#live-status");}', 'message("Sample preloaded",false,"#live-status");if(location.hash==="#playground")$("#method").textContent=example.method;if(latestResult&&latestResult.sample!==example.id)$("#live-results").hidden=true;}'),
 ('const result=state.result;if(!result?.images', 'const result=state.result;latestResult=result;if(!result?.images'),
 ('image("live-clean",result.images.edit_clean);', 'if(examples.length&&preloaded?.id!==result.sample){const match=examples.find(e=>e.id===result.sample);if(match)preload(match);}image("live-clean",result.images.edit_clean);'),
 ('loadExamples();pollLive();','loadExamples().then(()=>{if(latestResult){const match=examples.find(e=>e.id===latestResult.sample);if(match&&preloaded?.id!==match.id)preload(match);}});pollLive();'),
]
for old,new in changes:
    if s.count(old)!=1:raise ValueError('Expected unique UI source fragment.')
    s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
p=root/'frontend/research-demo/index.html';s=p.read_text()
assert s.count('</head>')==1
p.write_text(s.replace('</head>','<link rel="stylesheet" href="/static/flow.css"></head>'),encoding='utf-8')
print('Live result/sample and tab context synchronized.')
