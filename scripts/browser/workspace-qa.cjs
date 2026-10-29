const {chromium}=require('../../.cache/ui-test/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const out=path.resolve('outputs/workspace-qa');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const errors=[],requests=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('409'))errors.push(m.text());});
  page.on('request',r=>requests.push({method:r.method(),url:r.url()}));
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});await page.goto('http://127.0.0.1:8001/');
   await page.evaluate(()=>document.fonts.ready);
   await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth));
   checks.push(await page.evaluate(()=>({view:'landing',width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,serif:document.fonts.check('16px "Instrument Serif"'),inter:document.fonts.check('16px Inter')})));
   await page.screenshot({path:path.join(out,`landing-${width}.png`),fullPage:true});
  }
  await page.goto('http://127.0.0.1:8001/dashboard');await page.locator('#example-tabs button').nth(2).waitFor();
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});
   for(const view of ['comparisons','pipeline','playground','use-cases']){
    await page.locator(`.nav-item[href="#${view}"]`).click();
    await page.locator(`#${view}:not([hidden])`).waitFor();
    await page.waitForFunction(()=>Array.from(document.images).filter(i=>i.getClientRects().length).every(i=>i.complete&&i.naturalWidth));
    checks.push(await page.evaluate(view=>({view,width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,visibleImages:Array.from(document.images).filter(i=>i.getClientRects().length).length}),view));
    if(view==='pipeline'&&await page.locator('#pipeline-steps li img').count()!==8)throw new Error('Missing pipeline images');
    await page.screenshot({path:path.join(out,`${view}-${width}.png`),fullPage:true});
   }
  }
  await page.locator('.nav-item[href="#playground"]').click();
  for(const id of ['cap','tshirts','shorts']){
   await page.locator(`#preload-buttons button[data-id="${id}"]`).click();
   const src=await page.locator('#live-mask').getAttribute('src');
   if(src!==`/artifact/${id}/mask_overlay`)throw new Error('Mask overlay not preloaded');
  }
  await page.locator('#load-saved').click();await page.locator('#comparisons:not([hidden])').waitFor();
  if(await page.locator('#example-tabs button[data-id="shorts"]').getAttribute('aria-pressed')!=='true')throw new Error('Saved sample not restored');
  const passiveMutations=requests.filter(r=>r.method==='POST');
  if(passiveMutations.length)throw new Error('Browsing triggered model work');
  let live=null;
  if(process.argv.includes('--live')){
   await page.setViewportSize({width:1440,height:1000});await page.locator('.nav-item[href="#playground"]').click();
   await page.locator('#live-run').click();await page.locator('#live-run:disabled').waitFor();
   await page.waitForFunction(()=>!document.querySelector('#live-results').hidden||document.querySelector('#live-status').parentElement.classList.contains('error'),{},{timeout:300000});
   live=await(await page.request.get('http://127.0.0.1:8001/api/playground/state')).json();
   if(live.status!=='completed')throw new Error(JSON.stringify(live));
   await page.waitForFunction(()=>['live-clean','live-output'].every(id=>{const i=document.getElementById(id);return i.complete&&i.naturalWidth;}));
   await page.screenshot({path:path.join(out,'playground-completed.png'),fullPage:true});
  }
  const result={checks,errors,passiveModelRuns:passiveMutations.length,live};
  fs.writeFileSync(path.join(out,'checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  if(errors.length||checks.some(c=>c.overflow))throw new Error('Workspace visual checks failed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
