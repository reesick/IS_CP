"use strict";
const $ = selector => document.querySelector(selector);
const labels = {shorts:"Shorts",cap:"Cap",tshirts:"T-shirts",portrait:"Portrait"};
let examples = [], selected = null, preloaded = null, loaded = false, liveBusy = false, liveTimer, latestResult = null;
let pipeIndex = 0, pipePlay = null;
let clockOffset = 0, runStart = null, runTick = null, runJob = null, stageMarks = {};
let bgTimer = null, bgStart = null, bgTick = null, pendingSamples = [];
function findSample(id){return examples.find(e=>e.id===id)||pendingSamples.find(e=>e.id===id);}

function el(tag, cls, text){const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;}
function message(text,error=false,target="#status"){const node=$(target);node.textContent=text;node.parentElement.classList.toggle("error",error);}
function clock(seconds){seconds=Math.max(0,Math.floor(seconds));const m=Math.floor(seconds/60),s=seconds%60;return `${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;}
function serverNow(){return Date.now()/1000+clockOffset;}

function showView(){const views={comparisons:"Comparisons",pipeline:"Pipeline",playground:"Playground",verify:"Verify & audit","use-cases":"Use cases"};const view=Object.hasOwn(views,location.hash.slice(1))?location.hash.slice(1):"comparisons";for(const id of Object.keys(views))$("#"+id).hidden=(id!==view)||(!loaded&&["comparisons","pipeline"].includes(id));$("#saved-panel").hidden=["playground","use-cases","verify"].includes(view);if(view==="verify")loadAudit();$("#page-title").textContent=views[view];for(const link of document.querySelectorAll(".nav-item")){if(link.hash==="#"+view)link.setAttribute("aria-current","page");else link.removeAttribute("aria-current");}if(view!=="pipeline")stopPlay();}
window.addEventListener("hashchange",()=>{showView();const context=location.hash==="#playground"?preloaded:selected;if(context)$("#method").textContent=context.method;requestAnimationFrame(()=>window.scrollTo(0,0));});
function image(id,url){const node=$("#"+id);if(!node)return;node.src=url;const link=$("#"+id+"-link");if(link)link.href=url;}

/* ---------- Comparisons ---------- */
function showExample(example){
  selected=example;
  for(const [key,id] of Object.entries({clean_input:"clean-input",candidate_input:"candidate-input",edit_clean:"clean-result",edit_candidate:"candidate-result"}))image(id,example.images[key]);
  image("mask",example.images.mask_overlay||example.images.mask);$("#raw-mask-link").href=example.images.mask;
  if(example.images.perturbation){image("perturb",example.images.perturbation);const p=example.perturbation||{};$("#perturb-caption").textContent=`x${p.gain} · max ${p.max_255}/255`;}
  $("#method").textContent=example.method;$("#candidate-method").textContent=example.method;$("#example-prompt").textContent=example.prompt;$("#comparison-label").textContent=example.label;
  $("#result-meta").textContent=`Seed ${example.seed} · ${example.channel==="jpeg_simulation"?"JPEG simulation":"Local PNG"}`;
  const gate=example.quality_gate;const passed=gate===true||gate==="passed";const failed=gate===false||gate==="failed";
  const quality=$("#quality-status");quality.textContent=passed?"Invisible · fidelity passed":failed?"Visible noise":"Fidelity unverified";quality.classList.toggle("failed",failed);
  quality.title=failed?"Candidate contains visible noise and failed the fidelity gate.":"Input fidelity does not establish edit resistance.";
  const verdict=$("#verdict-badge");verdict.textContent=example.verdict?example.verdict.label:"";verdict.dataset.tone=example.verdict?example.verdict.tone:"";verdict.title=example.verdict?example.verdict.text:"";
  $("#safety-warning").hidden=!example.safety_filtered;
  for(const button of $("#example-tabs").querySelectorAll("button"))button.setAttribute("aria-pressed",String(button.dataset.id===example.id));
  buildPipeline(example);
  loaded=true;$("#example-details").hidden=false;message("Saved comparison");showView();
}

/* ---------- Pipeline ---------- */
const glyphs={Transform:"DCT",Encode:"VAE","Load model":"UNet"};
function buildPipeline(example){
  const flow=$("#pipe-flow");flow.replaceChildren();
  const steps=example.pipeline||[];
  $("#pipe-sample").textContent=`${example.label} · ${example.method}`;
  steps.forEach((step,index)=>{
    if(index>0){const link=el("li","pipe-link");link.setAttribute("aria-hidden","true");for(let i=0;i<3;i++)link.append(el("span","pipe-dot"));flow.append(link);}
    const li=el("li","pipe-item");const button=el("button","pipe-node");button.type="button";button.dataset.index=index;
    const thumb=el("span","pipe-thumb");
    if(step.image){const img=el("img");img.src=step.image;img.alt="";img.loading="lazy";thumb.append(img);}else{thumb.classList.add("glyph");thumb.textContent=glyphs[step.short]||"fx";}
    const meta=el("span","pipe-node-text");meta.append(el("span","pipe-node-num",String(index+1).padStart(2,"0")),el("span","pipe-node-title",step.short||step.title),el("span","pipe-node-phase",step.phase||""));
    button.append(thumb,meta);button.addEventListener("click",()=>{stopPlay();selectStep(index);});
    li.append(button);flow.append(li);
  });
  selectStep(Math.min(pipeIndex,steps.length-1));
}
function selectStep(index){
  const steps=selected?.pipeline||[];if(!steps.length)return;
  pipeIndex=(index+steps.length)%steps.length;const step=steps[pipeIndex];
  const nodes=[...$("#pipe-flow").querySelectorAll(".pipe-node")];const links=[...$("#pipe-flow").querySelectorAll(".pipe-link")];
  nodes.forEach((node,i)=>{node.classList.toggle("active",i===pipeIndex);node.classList.toggle("done",i<pipeIndex);if(i===pipeIndex)node.setAttribute("aria-current","step");else node.removeAttribute("aria-current");});
  links.forEach((link,i)=>{link.classList.toggle("flowing",i<pipeIndex);link.classList.toggle("next",i===pipeIndex-1);});
  const wrap=$(".pipe-flow-wrap"),node=nodes[pipeIndex];
  if(node&&wrap&&!wrap.hidden){const target=node.offsetLeft-(wrap.clientWidth-node.offsetWidth)/2;wrap.scrollTo({left:Math.max(0,target),behavior:"smooth"});}
  $("#pipe-phase").textContent=step.phase||"";$("#pipe-count").textContent=`Step ${pipeIndex+1} of ${steps.length}`;
  $("#pipe-title").textContent=step.title;$("#pipe-detail").textContent=step.detail;
  const status=$("#pipe-status");const tones={pass:"Invisible",fail:"Visible noise"};
  status.hidden=!step.status;if(step.status){status.textContent=tones[step.status]||selected.verdict?.label||"Review";status.dataset.tone=step.status;}
  const specs=$("#pipe-specs");specs.replaceChildren();for(const [k,v] of step.specs||[]){const row=el("div","pipe-spec");row.append(el("dt","",k),el("dd","",v));specs.append(row);}
  const box=$("#pipe-visual-box");box.replaceChildren();box.className="pipe-visual-box";
  const img=selected.images;
  if(step.short==="Optimise"&&img.perturbation){
    box.classList.add("equation");
    const part=(src,cap)=>{const f=el("figure","eq-part");const i=el("img");i.src=src;i.alt=cap;f.append(i,el("figcaption","",cap));return f;};
    box.append(part(img.clean_input,"Original x"),el("span","eq-op","+"),part(img.perturbation,"Change δ (amplified)"),el("span","eq-op","="),part(img.candidate_input,"Protected x + δ"));
  }else if(step.image){const i=el("img");i.src=step.image;i.alt=step.image_label||step.title;box.append(i);}
  else{box.classList.add("formula");const parts=(step.formula||step.title).split(/\s+>\s+/);parts.forEach((p,i)=>{if(i)box.append(el("span","formula-arrow","↓"));box.append(el("span","formula-chip",p));});}
  $("#pipe-image-label").textContent=step.image_label||"";
}
function stopPlay(){if(pipePlay){clearInterval(pipePlay);pipePlay=null;}const b=$("#pipe-play");if(b){b.textContent="Play";b.setAttribute("aria-pressed","false");}}
$("#pipe-play").addEventListener("click",()=>{if(pipePlay){stopPlay();return;}const b=$("#pipe-play");b.textContent="Pause";b.setAttribute("aria-pressed","true");selectStep(0);pipePlay=setInterval(()=>{if(pipeIndex>=(selected?.pipeline?.length||1)-1){stopPlay();return;}selectStep(pipeIndex+1);},3200);});
$("#pipe-prev").addEventListener("click",()=>{stopPlay();selectStep(pipeIndex-1);});
$("#pipe-next").addEventListener("click",()=>{stopPlay();selectStep(pipeIndex+1);});
document.addEventListener("keydown",e=>{if(location.hash!=="#pipeline"||["INPUT","TEXTAREA","SELECT"].includes(document.activeElement?.tagName))return;if(e.key==="ArrowRight"){stopPlay();selectStep(pipeIndex+1);}if(e.key==="ArrowLeft"){stopPlay();selectStep(pipeIndex-1);}});

/* ---------- Playground ---------- */
function canRun(){return Boolean(preloaded?.images?.candidate_input);}
function preload(example){if(liveBusy)return;const same=preloaded?.id===example.id;preloaded=example;if(!same){$("#live-prompt").value=example.prompt;$("#live-seed").value=example.seed||11;$("#live-channel").value="local_png";}image("live-source",example.images.clean_input);
  const cand=$("#live-candidate");const waiting=!example.images.candidate_input;cand.closest("figure").classList.toggle("waiting",waiting);if(waiting)cand.removeAttribute("src");else image("live-candidate",example.images.candidate_input);
  $("#live-run").disabled=waiting;if(waiting){message("Face loaded. Its protected version is still being generated in the background; Run unlocks automatically.",false,"#live-status");}image("live-mask",example.images.mask_overlay||example.images.mask);$("#preload-label").textContent=labels[example.id]||example.label;for(const button of $("#preload-buttons").querySelectorAll("button"))button.setAttribute("aria-pressed",String(button.dataset.id===example.id));if(!waiting)message("Sample preloaded",false,"#live-status");if(location.hash==="#playground")$("#method").textContent=example.method;if(latestResult&&latestResult.sample!==example.id&&!liveBusy)$("#live-results").hidden=true;}
async function request(url,options){const response=await fetch(url,{cache:"no-store",...options});let data;try{data=await response.json();}catch{throw new Error(`Invalid server response (${response.status}).`);}if(!response.ok){const error=new Error(typeof data.detail==="string"?data.detail:data.error||`Request failed (${response.status}).`);error.status=response.status;throw error;}return data;}
function setLiveBusy(busy){liveBusy=busy;for(const element of $("#playground-form").elements)element.disabled=busy;for(const button of $("#preload-buttons").querySelectorAll("button"))button.disabled=busy;$("#live-run").textContent=busy?"Running SD1.5…":"Run SD1.5";if(!busy)$("#live-run").disabled=!canRun();$("#live-results").classList.toggle("pending",busy);}

const order=["load","clean","protected","save"];
function stageOf(state){if(state.status==="completed")return "done";if(state.status==="failed")return "failed";if(state.phase!=="editing")return "load";if(state.total&&state.completed>=state.total)return "save";return /protected/i.test(state.stage||"")?"protected":"clean";}
function renderRun(state){
  const panel=$("#run-panel");panel.hidden=false;
  if(state.now)clockOffset=state.now-Date.now()/1000;
  if(state.job_id!==runJob){runJob=state.job_id;stageMarks={};}
  runStart=state.started_at||runStart;
  const stage=stageOf(state);const elapsed=(state.finished_at||serverNow())-(runStart||serverNow());
  if(order.includes(stage)&&stageMarks[stage]===undefined)stageMarks[stage]=elapsed;
  let current=stage==="done"?order.length:order.indexOf(stage);
  if(stage==="failed")current=Math.max(0,...order.map((s,i)=>stageMarks[s]!==undefined?i:0));
  [...$("#run-steps").children].forEach((li,i)=>{const name=li.dataset.stage;li.className=i<current?"done":i===current?(stage==="failed"?"error":"active"):"";
    const start=stageMarks[name];const end=stageMarks[order[i+1]]??(state.finished_at?elapsed:undefined);
    li.querySelector(".run-time").textContent=(i<current&&start!==undefined&&end!==undefined)?`${Math.max(0,end-start).toFixed(1)} s`:(i===current&&stage!=="failed"?"running":"");});
  const fill=$("#run-fill");const bar=fill.parentElement;
  if(stage==="load"){bar.classList.add("indeterminate");fill.style.width="30%";}
  else{bar.classList.remove("indeterminate");fill.style.width=stage==="done"?"100%":`${Math.round(100*(state.completed||0)/(state.total||1))}%`;}
  panel.classList.toggle("finished",state.status!=="running");panel.classList.toggle("failed",state.status==="failed");
  if(state.status==="running"){
    $("#run-title").textContent=state.stage||"Running SD1.5 on your GPU";
    $("#run-note").textContent=stage==="load"?(state.warm?"Model already in memory, starting quickly.":"First run loads about 2.7 GB of weights onto the GPU. Later runs are faster."):(state.total?`Denoising step ${state.completed} of ${state.total} across both edits.`:"");
    $("#run-timer").textContent=clock(elapsed);
    if(!runTick)runTick=setInterval(()=>{$("#run-timer").textContent=clock(serverNow()-(runStart||serverNow()));},250);
  }else{
    clearInterval(runTick);runTick=null;
    const total=Number(state.result?.runtime_seconds??elapsed);$("#run-timer").textContent=clock(total);
    if(state.status==="completed"){$("#run-title").textContent=`Completed in ${total.toFixed(1)} s`;$("#run-note").textContent=state.warm?"Model was already loaded (warm run).":"Included loading the model (cold run).";}
    else{$("#run-title").textContent="Run failed";$("#run-note").textContent=state.error||"";}
  }
}
function liveState(state){
  clearTimeout(liveTimer);setLiveBusy(state.status==="running");
  if(state.status==="running"){
    renderRun(state);$("#live-results").hidden=false;message(state.progress||"Running local SD1.5…",false,"#live-status");liveTimer=setTimeout(pollLive,700);
  }else if(state.status==="completed"){
    renderRun(state);const result=state.result;latestResult=result;
    if(!result?.images?.edit_clean||!result.images.edit_candidate)throw new Error("Completed test has no output pair.");
    if(examples.length&&preloaded?.id!==result.sample){const match=examples.find(e=>e.id===result.sample);if(match)preload(match);}
    image("live-clean",result.images.edit_clean);image("live-output",result.images.edit_candidate);
    $("#live-result-meta").textContent=`${labels[result.sample]||result.sample} · Seed ${result.seed} · ${result.channel==="jpeg_simulation"?"JPEG":"PNG"}${result.runtime_seconds?` · ${result.runtime_seconds} s`:""}`;
    $("#live-result-prompt").textContent=result.prompt;$("#live-safety").hidden=!result.safety_filtered;$("#live-results").hidden=false;
    message(result.safety_filtered?"Completed · Safety filtered":"Completed",false,"#live-status");
  }else if(state.status==="failed"){renderRun(state);$("#live-results").hidden=true;message(state.error||"Local test failed.",true,"#live-status");}
  else if(state.status==="idle")message("Ready",false,"#live-status");
}
async function pollLive(){try{liveState(await request("/api/playground/state"));}catch(error){clearTimeout(liveTimer);setLiveBusy(false);message(`${error.message} Reload to reconnect.`,true,"#live-status");}}
$("#load-saved").addEventListener("click",()=>{if(preloaded){showExample(preloaded);location.hash="comparisons";}});
$("#playground-form").addEventListener("submit",async event=>{event.preventDefault();if(liveBusy||!preloaded)return;const prompt=$("#live-prompt").value.trim(),seed=Number($("#live-seed").value),channel=$("#live-channel").value;if(!prompt||prompt.length>500||!Number.isInteger(seed)||seed<0||seed>4294967295){message("Enter a prompt and a valid integer seed.",true,"#live-status");return;}setLiveBusy(true);$("#live-results").hidden=false;message("Submitting local test…",false,"#live-status");try{liveState(await request("/api/playground/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({sample:preloaded.id,prompt,seed,channel})}));}catch(error){setLiveBusy(false);message(error.message,true,"#live-status");if(error.status===409)await pollLive();}});

/* ---------- Samples ---------- */
function addExampleButtons(example){for(const [container,pre] of [["#example-tabs",false],["#preload-buttons",true]]){if($(container).querySelector(`[data-id="${example.id}"]`))continue;const button=document.createElement("button");button.type="button";button.dataset.id=example.id;button.textContent=(pre?"Preload ":"")+(labels[example.id]||example.label);button.setAttribute("aria-pressed","false");button.disabled=pre&&liveBusy;button.addEventListener("click",()=>{const current=findSample(example.id);if(!current)return;if(pre)preload(current);else if(examples.includes(current))showExample(current);});$(container).append(button);}}
function addPendingButton(sample){if($("#preload-buttons").querySelector(`[data-id="${sample.id}"]`))return;const button=document.createElement("button");button.type="button";button.dataset.id=sample.id;button.textContent="Preload "+(labels[sample.id]||sample.label);button.setAttribute("aria-pressed","false");button.disabled=liveBusy;button.addEventListener("click",()=>{const current=findSample(sample.id);if(current)preload(current);});$("#preload-buttons").append(button);}
async function loadExamples(){try{const data=await request("/api/examples");if(!Array.isArray(data.examples)||!data.examples.length)throw new Error("No saved comparisons available.");const fresh=!examples.length;examples=data.examples;pendingSamples=data.pending||[];examples.forEach(addExampleButtons);pendingSamples.forEach(addPendingButton);if(preloaded&&!liveBusy){const current=findSample(preloaded.id);if(current&&current!==preloaded)preload(current);}if(fresh){const first=examples.find(e=>e.id==="shorts")||examples[0];showExample(first);preload(first);}}catch(error){message(error.message,true);message(error.message,true,"#live-status");}}

/* ---------- Background portrait job ---------- */
async function pollBackground(){
  clearTimeout(bgTimer);let state;try{state=await request("/api/background");}catch{bgTimer=setTimeout(pollBackground,10000);return;}
  if(state.now)clockOffset=state.now-Date.now()/1000;
  const banner=$("#bg-banner");const running=state.state==="running";
  if(!state.loaded)await loadExamples();
  else if(preloaded&&!preloaded.images.candidate_input)await loadExamples();
  if(!running&&state.state!=="failed"){banner.hidden=true;clearInterval(bgTick);bgTick=null;bgTimer=setTimeout(pollBackground,running?3000:8000);return;}
  banner.hidden=false;banner.classList.toggle("failed",state.state==="failed");
  bgStart=state.started_at||bgStart;
  const phase=state.phase==="edit"?"Tamper test":"Protection";const who=state.label||"Face";
  const queue=(state.queued||[]).length?` · next: ${state.queued.join(", ")}`:"";
  $("#bg-title").textContent=state.state==="failed"?`${who} run failed`:`${who} · ${phase}`;
  $("#bg-stage").textContent=state.state==="failed"?(state.error||""):`${state.stage||""}${state.total?` · ${state.completed}/${state.total}`:""}${queue}`;
  $("#bg-fill").style.width=state.total?`${Math.round(100*state.completed/state.total)}%`:"5%";
  if(running&&!bgTick)bgTick=setInterval(()=>{$("#bg-time").textContent=bgStart?`${clock(serverNow()-bgStart)} elapsed`:"";},500);
  if(!running){clearInterval(bgTick);bgTick=null;}
  bgTimer=setTimeout(pollBackground,running?3000:8000);
}

/* ---------- Verify & audit ---------- */
const verdictTone={VERIFIED:"good",MODIFIED:"warn",TAMPERED:"bad",UNKNOWN:"neutral",INVALID:"bad"};
function short(h){return h?h.slice(0,12)+"…":"";}
async function loadAudit(){
  let data;try{data=await request("/api/audit");}catch(e){$("#chain-status").textContent=e.message;return;}
  const c=data.chain,cs=$("#chain-status");cs.textContent=c.ok?`Chain intact · ${c.count} entries · head ${short(c.head)}`:`Chain BROKEN at entry ${c.broken_at}: ${c.reason}`;cs.dataset.tone=c.ok?"good":"bad";
  const body=$("#audit-rows");body.replaceChildren();
  for(const e of data.entries){const tr=el("tr");const subject=e.action==="REGISTER"?`${e.label} (${Object.keys(e.files||{}).length} files)`:`${e.filename||""}`;
    const res=e.action==="REGISTER"?"registered":`${e.verdict}${e.matched?" · "+e.matched:""}`;
    const cells=[String(e.seq),(e.time||"").replace("T"," ").slice(0,19),e.action+(e.source&&e.source!=="dashboard"?` (${e.source})`:""),subject,res,short(e.entry_hash),short(e.prev_hash)];
    cells.forEach((t,i)=>{const td=el("td","",t);if(i===4&&e.verdict)td.dataset.tone=verdictTone[e.verdict]||"";if(i>=5)td.className="mono";tr.append(td);});body.append(tr);}
  const reg=$("#registry");reg.replaceChildren();let n=0;
  for(const s of data.registry){const card=el("div","reg-card");card.append(el("h3","",s.label));const row=el("div","reg-row");
    for(const it of s.items){n++;const f=el("figure","reg-item");const img=el("img");img.src=it.image;img.alt=it.role_label;img.loading="lazy";f.append(img,el("figcaption","",it.role_label),el("code","",short(it.sha256)));row.append(f);}
    card.append(row);reg.append(card);}
  $("#registry-count").textContent=`${n} images across ${data.registry.length} samples`;
}
async function verifyFile(file){
  if(!file)return;const box=$("#verify-result");box.hidden=false;$("#v-verdict").textContent="Checking…";$("#v-verdict").dataset.tone="neutral";$("#v-summary").textContent=file.name;
  const url=URL.createObjectURL(file);$("#v-probe").src=url;$("#v-match").removeAttribute("src");$("#v-details").replaceChildren();
  try{const r=await request("/api/verify",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-Filename":encodeURIComponent(file.name).slice(0,200)},body:file});
    $("#v-verdict").textContent=r.verdict;$("#v-verdict").dataset.tone=verdictTone[r.verdict]||"neutral";$("#v-summary").textContent=r.summary;
    if(r.match){$("#v-match").src=r.match.image;$("#v-match-label").textContent=`Matched: ${r.match.role_label} · ${r.match.label}`;}else $("#v-match-label").textContent="No matching record";
    const rows=[["Verdict",r.verdict],["SHA-256",r.sha256],["Size",r.size?`${r.size[0]} x ${r.size[1]}`:"-"],["Matched record",r.match?`${r.match.label} / ${r.match.role}`:"none"],["Similarity",r.similarity!=null?`${r.similarity}%`:"-"],["Pixels changed",r.pixels_changed!=null?`${r.pixels_changed}%`:"different size or re-encoded"],["Protection present",r.protection_present?"yes":"no"],["Audit entry",`#${r.audit_seq} · ${short(r.audit_hash)}`]];
    for(const [k,v] of rows){const d=el("div","pipe-spec");d.append(el("dt","",k),el("dd","",v));$("#v-details").append(d);}
  }catch(e){$("#v-verdict").textContent="ERROR";$("#v-verdict").dataset.tone="bad";$("#v-summary").textContent=e.message;}
  loadAudit();
}
$("#verify-file").addEventListener("change",e=>verifyFile(e.target.files[0]));
const drop=$("#drop");["dragenter","dragover"].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add("over");}));
["dragleave","drop"].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove("over");}));
drop.addEventListener("drop",e=>verifyFile(e.dataTransfer.files[0]));

showView();
loadExamples().then(()=>{if(latestResult){const match=examples.find(e=>e.id===latestResult.sample);if(match&&preloaded?.id!==match.id)preload(match);}});
pollLive();pollBackground();
