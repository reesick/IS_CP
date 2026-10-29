import {MaskEditor} from './mask-editor.js';
const $=id=>document.getElementById(id), API='/api/v1';
let asset=null, maskId=null, protectionJob=null, protectionMaskId=null, activeJob=null, activeKind=null, experiment=null, pollTimer=null, capability=null, uploading=false;
function persist(){try{localStorage.setItem('imageshield-workspace',JSON.stringify({asset_id:asset?.id,mask_id:maskId,protection_mask_id:protectionMaskId,protection_job_id:protectionJob?.id,active_job_id:activeJob,active_kind:activeKind,experiment_id:experiment?.id,rect:editor.rect,mode:editor.mode}));}catch{}}
const artifactURL=id=>`${API}/artifacts/${encodeURIComponent(typeof id==='object'?(id.id||id.artifact_id):id)}`;
const errorMessage=error=>error.message || 'Something went wrong. Try again.';
function showError(id,error){const node=$(id);node.textContent=error?errorMessage(error):'';node.hidden=!error;}
function announce(text){$('announcement').textContent=text;}
async function request(path,options={}){
  const response=await fetch(API+path,{credentials:'same-origin',...options});
  let value;try{value=await response.json();}catch{value={};}
  if(!response.ok)throw new Error(value.error?.message || (typeof value.detail==='string'?value.detail:null) || `Request failed (${response.status}).`);
  return value;
}
const json=data=>({headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
function navigate(){const hash=location.hash.slice(1),view=['protect','attack-lab','verify'].includes(hash)?hash:'protect';document.querySelectorAll('.view').forEach(node=>node.hidden=node.id!==view);document.querySelectorAll('nav a').forEach(link=>{if(link.hash===`#${view}`)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});document.title=`${view==='attack-lab'?'Attack Lab':view==='verify'?'Verify':'Protect'} · ImageShield`;}
window.addEventListener('hashchange',navigate);navigate();
document.querySelector('nav').addEventListener('keydown',event=>{if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;const links=[...document.querySelectorAll('nav a')],index=links.indexOf(document.activeElement);if(index<0)return;event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?links.length-1:(index+(event.key==='ArrowRight'?1:-1)+links.length)%links.length;links[next].focus();location.hash=links[next].hash;});
try{if(localStorage.getItem('imageshield-theme')==='dark')document.documentElement.dataset.theme='dark';}catch{}
function updateThemeLabel(){$('theme').setAttribute('aria-label',`Switch to ${document.documentElement.dataset.theme==='dark'?'light':'dark'} theme`);document.querySelector('meta[name="theme-color"]').content=document.documentElement.dataset.theme==='dark'?'#09090b':'#fafafa';}
$('theme').addEventListener('click',()=>{const dark=document.documentElement.dataset.theme!=='dark';document.documentElement.dataset.theme=dark?'dark':'light';try{localStorage.setItem('imageshield-theme',dark?'dark':'light');}catch{}updateThemeLabel();});updateThemeLabel();
async function capabilities(){
  try{capability=await request('/capabilities');const ready=Boolean(capability.ready);$('capability').textContent=ready?'GPU ready':'Setup required';$('capability').classList.toggle('ready',ready);$('setup-notice').hidden=ready;$('setup-title').textContent=!capability.cuda?'GPU setup required':!capability.model_ready?'Model files are not installed.':'Protection setup required';$('setup-message').textContent=(capability.reasons || []).join(' ') || 'Upload and region selection are available while setup is completed.';$('capability-details').textContent=JSON.stringify(capability,null,2);if(capability.setup_command){const para=$('capability-details').nextElementSibling;para.textContent=`Setup command: ${capability.setup_command}`;}}
  catch(error){$('capability').textContent='API unavailable';$('setup-notice').hidden=false;$('setup-title').textContent='The local API is unavailable';$('setup-message').textContent=errorMessage(error);}
}
$('refresh-capabilities').addEventListener('click',capabilities);capabilities();
const editor=new MaskEditor($('mask-canvas'),rect=>{
  maskId=null;
  for(const field of ['x','y','width','height'])$('region-'+field).value=rect?.[field] || 0;
  const fraction=editor.editableFraction();$('selection-info').textContent=rect?.width&&rect?.height?`${Math.round(fraction*100)}% editable · ${rect.width} × ${rect.height} region`:'No region selected';
  persist();
});
$('mask-mode').addEventListener('change',()=>editor.setMode($('mask-mode').value));$('clear-selection').addEventListener('click',()=>editor.clear());
for(const field of ['x','y','width','height'])$('region-'+field).addEventListener('change',()=>editor.setRect(Object.fromEntries(['x','y','width','height'].map(key=>[key,$('region-'+key).value]))));
$('choose-image').addEventListener('click',()=>$('image-file').click());$('replace-image').addEventListener('click',()=>$('image-file').click());
$('image-file').addEventListener('change',event=>{const file=event.target.files[0];if(file)upload(file);event.target.value='';});
for(const name of ['dragenter','dragover'])$('upload-zone').addEventListener(name,event=>{event.preventDefault();$('upload-zone').classList.add('dragover');});
for(const name of ['dragleave','drop'])$('upload-zone').addEventListener(name,event=>{event.preventDefault();$('upload-zone').classList.remove('dragover');});
$('upload-zone').addEventListener('drop',event=>{if(event.dataTransfer.files[0])upload(event.dataTransfer.files[0]);});
async function upload(file){
  if(uploading)return;
  showError('upload-error',null);if(activeJob){showError('upload-error',new Error('Wait for the current job to finish, or cancel it first.'));return;}
  if(file.size>10*1024*1024){showError('upload-error',new Error('Choose an image smaller than 10 MB.'));return;}
  if(!['image/png','image/jpeg'].includes(file.type)){showError('upload-error',new Error('Choose a PNG or JPEG image.'));return;}
  const button=$('choose-image');uploading=true;button.disabled=true;button.textContent='Uploading…';
  try{
    // Give transparent PNGs an explicit compositing preview before upload.
    if(file.type==='image/png'){
      const bitmap=await createImageBitmap(file);const check=document.createElement('canvas');check.width=Math.min(bitmap.width,256);check.height=Math.min(bitmap.height,256);const ctx=check.getContext('2d',{willReadFrequently:true});ctx.drawImage(bitmap,0,0,check.width,check.height);const pixels=ctx.getImageData(0,0,check.width,check.height).data;let alpha=false;for(let i=3;i<pixels.length;i+=4)if(pixels[i]<255){alpha=true;break;}bitmap.close();
      if(alpha && !await confirmAlpha(file)){return;}
    }
    const form=new FormData();form.append('file',file);const result=await request('/assets',{method:'POST',body:form});
    asset=result;asset.id=asset.id||asset.asset_id;maskId=null;protectionJob=null;protectionMaskId=null;experiment=null;
    await editor.load(artifactURL(asset.preview_artifact_id || asset.artifacts?.preview),asset.geometry);
    $('workspace').hidden=false;$('upload-zone').hidden=true;$('image-title').textContent=file.name;$('asset-details').textContent=JSON.stringify(asset.geometry,null,2);$('protection-result').hidden=true;$('rejected-result').hidden=true;$('job-status').hidden=true;$('protected-preview').hidden=true;$('mask-canvas').hidden=false;$('show-original').hidden=true;showError('protect-error',null);$('attack-empty').hidden=false;$('attack-form').hidden=true;$('experiment-results').hidden=true;persist();announce('Image uploaded. Select a region to protect.');
  }catch(error){showError('upload-error',error);}finally{uploading=false;button.disabled=false;button.textContent='Choose image';}
}
async function confirmAlpha(file){
  return new Promise(resolve=>{
    const dialog=document.createElement('dialog');dialog.className='panel alpha-dialog';
    const heading=document.createElement('h2');heading.textContent='Transparency needs a background';const text=document.createElement('p');text.textContent='The research export composites transparent pixels on a neutral #f4f4f5 background. Review the preview before continuing.';
    const image=document.createElement('img');image.className='alpha-preview';image.alt='Transparency preview on neutral #f4f4f5 background';const url=URL.createObjectURL(file);image.src=url;
    const row=document.createElement('div');row.className='actions';const cancel=document.createElement('button');cancel.textContent='Choose another image';const accept=document.createElement('button');accept.className='primary';accept.textContent='Continue with neutral background';const finish=value=>{URL.revokeObjectURL(url);dialog.close();dialog.remove();resolve(value);};cancel.onclick=()=>finish(false);accept.onclick=()=>finish(true);dialog.addEventListener('cancel',event=>{event.preventDefault();finish(false);});row.append(cancel,accept);dialog.append(heading,text,image,row);document.body.append(dialog);dialog.showModal();accept.focus();
  });
}
function busy(value){$('protect-image').disabled=value;$('cancel-job').hidden=!value;editor.enabled=!value;for(const id of ['mask-mode','profile','seed','epsilon','clear-selection','replace-image','region-x','region-y','region-width','region-height'])$(id).disabled=value;$('protect-image').replaceChildren();if(value){const spinner=document.createElement('span');spinner.className='spinner';spinner.setAttribute('aria-hidden','true');$('protect-image').append(spinner);}$('protect-image').append(document.createTextNode('Protect image'));}
async function saveMask(){const blob=await editor.blob();const form=new FormData();form.append('file',blob,'edit-mask.png');const mask=await request(`/assets/${asset.id}/mask`,{method:'PUT',body:form});maskId=mask.mask_id;return maskId;}
$('protect-image').addEventListener('click',async()=>{
  showError('protect-error',null);if(!asset)return;busy(true);
  try{await saveMask();const result=await request(`/assets/${asset.id}/protect`,{method:'POST',...json({method:'diffusionguard',profile:$('profile').value,mask_id:maskId,watermark:false,seed:Number($('seed').value),epsilon:Number($('epsilon').value)/255})});activeJob=result.id||result.job_id;activeKind='protect';protectionMaskId=maskId;protectionJob=null;persist();$('protection-result').hidden=true;$('rejected-result').hidden=true;$('job-status').hidden=false;await pollProtection();}
  catch(error){showError('protect-error',error);busy(false);activeJob=null;}
});
$('cancel-job').addEventListener('click',async()=>{if(!activeJob)return;try{await request(`/jobs/${activeJob}/cancel`,{method:'POST'});$('job-stage').textContent='Cancellation requested; waiting for a safe iteration boundary.';}catch(error){showError('protect-error',error);}});
function jobText(job){const stage=(job.stage||job.state).replaceAll('_',' ');return job.total_steps?`${stage} · ${job.completed_steps || 0} / ${job.total_steps} iterations`:stage;}
async function pollProtection(){
  if(!activeJob)return;
  try{const job=await request(`/jobs/${activeJob}`);$('job-title').textContent=job.state==='queued'?'Waiting for the worker':job.state==='running'?'Generating protection':job.state.replaceAll('_',' ');$('job-stage').textContent=jobText(job);$('job-status').classList.toggle('running',['queued','running'].includes(job.state));
    if(['queued','running'].includes(job.state)){pollTimer=setTimeout(pollProtection,1500);return;}
    activeJob=null;activeKind=null;busy(false);
    if(job.state==='succeeded'){protectionJob=job;renderProtection(job.output||job.output_json||job);announce('Protection generated. Effectiveness has not been tested.');}
    else{if(job.state==='rejected_quality'){protectionJob=job;renderRejected(job.output);}showError('protect-error',new Error(job.error_message || (job.state==='rejected_quality'?'The protected export did not pass the image-quality gate. Adjust settings and try again.':job.state==='cancelled'?'Job cancelled.':`Protection failed (${job.error_code || job.state}).`)));}persist();
  }catch(error){showError('protect-error',new Error(`${errorMessage(error)} Reconnecting to the worker…`));pollTimer=setTimeout(pollProtection,5000);}
}
function renderProtection(output){
  const id=output.artifacts?.protected;if(!id){showError('protect-error',new Error('The job returned no protected artifact.'));return;}
  $('protection-result').hidden=false;$('download-protected').href=artifactURL(id);$('protected-preview').src=artifactURL(id);$('protected-preview').hidden=false;$('mask-canvas').hidden=true;$('show-original').hidden=false;$('show-original').textContent='Show original';
  $('quality-metrics').replaceChildren();for(const [key,label,suffix] of [['psnr_db','PSNR',' dB'],['ssim','SSIM','']]){const item=document.createElement('div');item.className='metric';const number=document.createElement('strong');const val=output.quality?.[key];number.textContent=typeof val==='number'?`${val.toFixed(key==='ssim'?4:1)}${suffix}`:'Unavailable';const name=document.createElement('span');name.textContent=label;item.append(number,name);$('quality-metrics').append(item);}
  $('result-details').textContent=JSON.stringify(output,null,2);$('attack-empty').hidden=true;$('attack-form').hidden=false;protectionMaskId=output.scope?.mask||protectionMaskId;persist();
}
function renderRejected(output){
  if(!output)return;$('protection-result').hidden=true;$('rejected-result').hidden=false;$('attack-empty').hidden=false;$('attack-form').hidden=true;$('rejected-metrics').replaceChildren();for(const [key,label]of [['psnr_db','PSNR (dB)'],['ssim','SSIM'],['max_absolute_difference','Max pixel difference']]){const value=output.quality?.[key];if(value===undefined)continue;const item=document.createElement('div');item.className='metric';const number=document.createElement('strong');number.textContent=typeof value==='number'?value.toFixed(key==='psnr_db'?1:4):'Unavailable';const name=document.createElement('span');name.textContent=label;item.append(number,name);$('rejected-metrics').append(item);}$('rejected-details').textContent=JSON.stringify(output,null,2);$('download-diagnostic').hidden=!output.artifacts?.diagnostic;if(output.artifacts?.diagnostic)$('download-diagnostic').href=artifactURL(output.artifacts.diagnostic);
}
$('adjust-settings').addEventListener('click',()=>{$('advanced-protection').open=true;$('epsilon').focus();$('advanced-protection').scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});});
$('show-original').addEventListener('click',()=>{const showingProtected=!$('protected-preview').hidden;$('protected-preview').hidden=showingProtected;$('mask-canvas').hidden=!showingProtected;$('show-original').textContent=showingProtected?'Show protected':'Show original';});
$('delete-asset').addEventListener('click',async()=>{if(!asset)return;if(!confirm('Delete this image and its local artifacts? Related jobs will be cancelled.'))return;try{await request(`/assets/${asset.id}`,{method:'DELETE'});clearTimeout(pollTimer);asset=null;protectionJob=null;activeJob=null;busy(false);$('workspace').hidden=true;$('upload-zone').hidden=false;$('attack-empty').hidden=false;$('attack-form').hidden=true;$('experiment-results').hidden=true;announce('Image and associated artifacts deleted.');}catch(error){showError('protect-error',error);}});
$('attack-form').addEventListener('submit',async event=>{
  event.preventDefault();showError('attack-error',null);if(!asset||!protectionJob)return;if(activeJob){showError('attack-error',new Error('Wait for the current job to finish or cancel it first.'));return;}
  const seeds=$('edit-seeds').value.split(',').map(v=>Number(v.trim()));if(!seeds.length||seeds.length>3||seeds.some(v=>!Number.isInteger(v)||v<0||v>2147483647)){showError('attack-error',new Error('Enter one to three integer seeds between 0 and 2147483647.'));return;}
  $('run-comparison').disabled=true;
  try{const result=await request(`/assets/${asset.id}/edit-tests`,{method:'POST',...json({protection_job_id:protectionJob.id,mask_id:protectionMaskId,prompt:$('edit-prompt').value.trim(),editor:'sd15_inpaint',seeds,channel:$('channel').value})});activeJob=result.id||result.job_id;activeKind='edit';persist();busy(true);$('cancel-comparison').hidden=false;$('attack-status').hidden=false;$('experiment-results').hidden=true;pollExperiment(activeJob);}
  catch(error){showError('attack-error',error);if(activeJob){const jobId=activeJob;pollTimer=setTimeout(()=>pollExperiment(jobId),5000);}else{$('run-comparison').disabled=false;}}
});
$('edit-prompt').addEventListener('keydown',event=>{if(event.key==='Enter'&&(event.ctrlKey||event.metaKey))$('attack-form').requestSubmit();});
async function pollExperiment(id){
  try{const job=await request(`/jobs/${id}`);$('attack-status').textContent=jobText(job);if(['queued','running'].includes(job.state)){pollTimer=setTimeout(()=>pollExperiment(id),1500);return;}activeJob=null;activeKind=null;busy(false);$('cancel-comparison').hidden=true;$('run-comparison').disabled=false;persist();if(job.state!=='succeeded')throw new Error(job.error_message||`Comparison ${job.state}.`);const output=job.output||job.output_json||job;experiment=await request(`/experiments/${output.experiment_id}`);renderExperiment();persist();announce('Paired edit comparison complete. Review the results.');}
  catch(error){showError('attack-error',error);$('run-comparison').disabled=false;}
}
function renderExperiment(){
  $('experiment-results').hidden=false;$('pair-seed').replaceChildren();for(const pair of experiment.pairs||[]){const option=document.createElement('option');option.value=pair.seed;option.textContent=pair.seed;$('pair-seed').append(option);}$('experiment-details').textContent=JSON.stringify(experiment,null,2);showPair();renderEffectiveness();
}
$('pair-seed').addEventListener('change',showPair);
function showPair(){
  const pair=experiment.pairs.find(p=>String(p.seed)===$('pair-seed').value);if(!pair)return;$('comparison-grid').replaceChildren();
  for(const [key,title] of [['clean','Original'],['protected','Protected'],['edit_clean','AI edit of original'],['edit_protected','AI edit of protected']]){const card=document.createElement('article');card.className='comparison-card';const heading=document.createElement('h3');heading.textContent=title;card.append(heading);if(pair[key]){const link=document.createElement('a');link.href=artifactURL(pair[key]);link.target='_blank';link.rel='noopener';link.setAttribute('aria-label',`Open ${title.toLowerCase()} at full size`);const img=document.createElement('img');img.src=link.href;img.alt=title;img.width=img.height=512;link.append(img);card.append(link);}else{const empty=document.createElement('div');empty.className='empty-image';empty.textContent='Output unavailable';card.append(empty);}$('comparison-grid').append(card);}
  const saved=experiment.review?.pairs?.find(p=>p.seed===pair.seed);$('review-fields').replaceChildren();for(const [key,title] of [['clean','AI edit of original'],['protected','AI edit of protected']]){const fieldset=document.createElement('fieldset');const legend=document.createElement('legend');legend.textContent=title;fieldset.append(legend);for(const [field,label,options]of [['requested_edit_completed','Requested edit completed?',[['uncertain','Uncertain'],['yes','Yes'],['no','No']]],['realism','Realism',[['1','1 · Poor'],['2','2'],['3','3'],['4','4'],['5','5 · Excellent']]],['retained_subject_fidelity','Retained-subject fidelity',[['1','1 · Poor'],['2','2'],['3','3'],['4','4'],['5','5 · Excellent']]]]){const labelNode=document.createElement('label');labelNode.htmlFor=`review-${key}-${field}`;labelNode.textContent=label;const select=document.createElement('select');select.id=labelNode.htmlFor;for(const [value,name]of options){const option=document.createElement('option');option.value=value;option.textContent=name;select.append(option);}select.value=saved?.[key]?.[field]??(field==='requested_edit_completed'?'uncertain':'3');fieldset.append(labelNode,select);}$('review-fields').append(fieldset);}$('review-notes').value=experiment.review?.notes||'';$('review-status').textContent='';
}
function renderEffectiveness(){const value=experiment.effectiveness||'inconclusive';const text={not_tested:'Effectiveness not tested.',inconclusive:'Result inconclusive. Human review is needed before interpreting edit disruption.',observed_disruption:'Observed disruption in these test conditions.',bypass_observed:'Edit succeeded in this test.'};$('effectiveness').textContent=text[value]||value;const review=experiment.review;if(review?.eligible_pairs!==undefined)$('effectiveness').textContent+=` ${review.disrupted_pairs} / ${review.eligible_pairs} eligible pairs disrupted · ${review.image_count} image(s).`;}
$('review-form').addEventListener('submit',async event=>{event.preventDefault();if(!experiment)return;const seed=Number($('pair-seed').value),review={seed};for(const key of ['clean','protected'])review[key]={requested_edit_completed:$(`review-${key}-requested_edit_completed`).value,realism:Number($(`review-${key}-realism`).value),retained_subject_fidelity:Number($(`review-${key}-retained_subject_fidelity`).value)};const defaults=()=>({requested_edit_completed:'uncertain',realism:3,retained_subject_fidelity:3});const pairs=experiment.pairs.map(pair=>pair.seed===seed?review:(experiment.review?.pairs||[]).find(prior=>prior.seed===pair.seed)||{seed:pair.seed,clean:defaults(),protected:defaults()});try{await request(`/experiments/${experiment.id}/review`,{method:'PUT',...json({pairs,notes:$('review-notes').value})});experiment=await request(`/experiments/${experiment.id}`);$('review-status').textContent='Review saved. Unreviewed pairs remain uncertain.';renderEffectiveness();$('experiment-details').textContent=JSON.stringify(experiment,null,2);}catch(error){$('review-status').textContent=errorMessage(error);}});
$('cancel-comparison').addEventListener('click',async()=>{if(!activeJob)return;try{await request(`/jobs/${activeJob}/cancel`,{method:'POST'});$('attack-status').textContent='Cancellation requested; waiting for a safe boundary.';}catch(error){showError('attack-error',error);}});
async function restoreWorkspace(){
  let saved;try{saved=JSON.parse(localStorage.getItem('imageshield-workspace')||'null');}catch{return;}if(!saved?.asset_id)return;
  try{
    const session=await request('/assets');const found=session.assets.find(item=>item.id===saved.asset_id);if(!found){localStorage.removeItem('imageshield-workspace');return;}
    asset=found;await editor.load(artifactURL(asset.preview_artifact_id),asset.geometry);editor.setMode(saved.mode||'selected');$('mask-mode').value=editor.mode;if(saved.rect)editor.setRect(saved.rect);maskId=saved.mask_id;protectionMaskId=saved.protection_mask_id;
    $('workspace').hidden=false;$('upload-zone').hidden=true;$('image-title').textContent='Saved working image';$('asset-details').textContent=JSON.stringify(asset.geometry,null,2);
    if(saved.protection_job_id){protectionJob=await request(`/jobs/${saved.protection_job_id}`);if(protectionJob.state==='succeeded')renderProtection(protectionJob.output);else if(protectionJob.state==='rejected_quality')renderRejected(protectionJob.output);}
    if(saved.experiment_id){experiment=await request(`/experiments/${saved.experiment_id}`);renderExperiment();}
    if(saved.active_job_id){activeJob=saved.active_job_id;activeKind=saved.active_kind;busy(true);if(activeKind==='edit'){$('attack-status').hidden=false;$('cancel-comparison').hidden=false;$('run-comparison').disabled=true;pollExperiment(activeJob);}else{$('job-status').hidden=false;pollProtection();}}
    persist();announce('Saved local workspace restored.');
  }catch(error){showError('upload-error',new Error(`The saved workspace could not be restored. ${errorMessage(error)}`));}
}
restoreWorkspace();
