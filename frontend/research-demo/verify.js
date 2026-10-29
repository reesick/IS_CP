"use strict";
const $=s=>document.querySelector(s);
function li(text,ok){const n=document.createElement("li");n.textContent=text;n.dataset.ok=ok;return n;}
const VIEW={
  protected:{tone:"good",icon:"✓",label:"ImageShield verified",title:"Protected by ImageShield"},
  protected_copy:{tone:"good",icon:"✓",label:"ImageShield verified",title:"Protected by ImageShield (modified copy)"},
  tampered:{tone:"bad",icon:"!",label:"Tampering detected",title:"AI-edited copy of a protected image"},
  original:{tone:"warn",icon:"i",label:"Registered, not protected",title:"Registered original without protection"},
  edit_original:{tone:"warn",icon:"!",label:"AI edit detected",title:"AI edit of an unprotected original"},
  source:{tone:"neutral",icon:"i",label:"Registered source",title:"Source photo registered before protection"},
  unknown:{tone:"neutral",icon:"?",label:"No record",title:"No ImageShield record for this image"},
  invalid:{tone:"bad",icon:"×",label:"Unreadable",title:"This file is not a readable image"}};
function kind(r){
  if(r.verdict==="INVALID")return"invalid";if(r.verdict==="UNKNOWN"||!r.match)return"unknown";
  const role=r.match.role;
  if(role==="edit_protected"||role==="jpeg_edit_protected")return"tampered";
  if(role==="edit_original"||role==="jpeg_edit_original")return"edit_original";
  if(role==="protected")return r.exact?"protected":"protected_copy";
  if(role==="source")return"source";return"original";}
async function check(file){
  if(!file)return;const box=$("#vresult");box.hidden=false;
  $("#vverdict").dataset.tone="neutral";$("#vicon").textContent="…";$("#vlabel").textContent="Checking";$("#vtitle").textContent=file.name;$("#vsummary").textContent="Comparing pixels with the evidence registry…";
  $("#vprobe").src=URL.createObjectURL(file);$("#vmatch").removeAttribute("src");["#vproof","#vmeta","#vdetails"].forEach(s=>$(s).replaceChildren());
  let r;try{const res=await fetch("/api/verify",{method:"POST",headers:{"Content-Type":"application/octet-stream","X-Filename":encodeURIComponent(file.name).slice(0,200)},body:file});
    r=await res.json();if(!res.ok)throw new Error(r.detail||"Verification failed");}
  catch(e){$("#vverdict").dataset.tone="bad";$("#vicon").textContent="×";$("#vlabel").textContent="Error";$("#vtitle").textContent="Could not verify";$("#vsummary").textContent=e.message;return;}
  const k=kind(r),v=VIEW[k];
  $("#vverdict").dataset.tone=v.tone;$("#vicon").textContent=v.icon;$("#vlabel").textContent=v.label;$("#vtitle").textContent=v.title;$("#vsummary").textContent=r.summary;
  if(r.match){$("#vmatch").src=r.match.image;$("#vmatchcap").textContent=`Registered: ${r.match.role_label} · ${r.match.label}`;}else{$("#vmatchcap").textContent="No matching record";}
  const p=$("#vproof");
  if(r.exact)p.append(li("Exact SHA-256 match with a registered file (byte-identical)","yes"));
  else if(r.match)p.append(li(`Perceptual fingerprint match: ${r.similarity}% similar (${r.confidence||"high"} confidence)`,"yes"));
  else p.append(li(`No fingerprint match (best similarity ${r.similarity??"n/a"}%)`,"no"));
  if(r.protection_signal!=null)p.append(li(r.protection_signal>0?"Protection pattern matched: closer to the protected export than to the clean original after replaying resize and JPEG":"Protection pattern absent: matches the clean original, not the protected export",r.protection_signal>0?"yes":"no"));
  else if(r.match)p.append(li(r.protection_present?"Derived from a protected export":"Not derived from a protected export",r.protection_present?"yes":"no"));
  if(r.pixels_changed!=null&&r.verdict!=="VERIFIED")p.append(li(`${r.pixels_changed}% of pixels differ from the registered file`,"info"));
  if(r.registered_at)p.append(li(`Registered in the evidence log on ${r.registered_at.replace("T"," ").slice(0,16)}`,"info"));
  p.append(li(`Recorded as audit entry #${r.audit_seq} in the SHA-256 hash chain`,"info"));
  const m=$("#vmeta"),md=r.metadata||{};
  m.append(li(md.c2pa?`C2PA content credentials present${md.claims.length?" (mentions "+md.claims.join(", ")+")":""}`:"No C2PA content credentials in this file",md.c2pa?"yes":"info"));
  m.append(li(md.exif?"EXIF metadata present":"No EXIF metadata",md.exif?"yes":"info"));
  if(md.claims&&md.claims.length&&!md.c2pa)m.append(li(`Generator names found in file: ${md.claims.join(", ")}`,"info"));
  m.append(li(r.match?"ImageShield's result above does not rely on any of this metadata":"Metadata alone cannot prove where an image came from",r.match?"yes":"info"));
  const d=$("#vdetails"),rows=[["SHA-256",r.sha256],["File",`${r.filename} · ${(r.bytes/1024).toFixed(1)} KB · ${md.format||"?"}`],["Size",r.size?`${r.size[0]} x ${r.size[1]}`:"same as record"],["Verdict",r.verdict],["Matched record",r.match?`${r.match.ref} · ${r.match.sha256}`:"none"],["Protection signal",r.protection_signal??"n/a"],["Audit entry hash",r.audit_hash]];
  for(const [a,b] of rows){const dt=document.createElement("dt");dt.textContent=a;const dd=document.createElement("dd");dd.textContent=String(b);d.append(dt,dd);}
  box.scrollIntoView({behavior:"smooth",block:"start"});}
$("#vfile").addEventListener("change",e=>check(e.target.files[0]));
const drop=$("#vdrop");["dragenter","dragover"].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add("over");}));
["dragleave","drop"].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove("over");}));
drop.addEventListener("drop",e=>check(e.dataTransfer.files[0]));
