const {chromium}=require('../../.cache/ui-test/node_modules/playwright');
const fs=require('fs');const path=require('path');
(async()=>{
 const out=path.resolve('outputs/local-sd15-demo/preloaded-qa');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];const requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('request',r=>requests.push({method:r.method(),url:r.url()}));
  await page.goto('http://127.0.0.1:8001/');
  await page.locator('#example-tabs button').nth(2).waitFor();
  const views=[];
  for(const width of [1440,390]) {
   await page.setViewportSize({width,height:1000});
   for(const id of ['shorts','cap','tshirts']) {
    await page.locator(`#example-tabs button[data-id="${id}"]`).click();
    await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth));
    const order=await page.locator('.comparison-flow img').evaluateAll(nodes=>nodes.map(n=>n.id));
    if(order.join(',')!=='clean-input,candidate-input,candidate-result')throw new Error('Incorrect original/protected/tampered ordering');
    const view=await page.evaluate(()=>({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,images:document.images.length,status:document.querySelector('#status').textContent}));
    views.push({id,...view});await page.screenshot({path:path.join(out,`${id}-${width}.png`),fullPage:true});
    await page.locator('.nav-item[href="#pipeline"]').click();
    await page.locator('#pipeline:not([hidden])').waitFor();
    if(await page.locator('#pipeline-steps li').count()!==8)throw new Error('Pipeline steps missing');
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Pipeline layout overflow');
    await page.screenshot({path:path.join(out,`${id}-pipeline-${width}.png`),fullPage:true});
    await page.locator('.nav-item[href="#comparisons"]').click();
    await page.locator('#comparisons:not([hidden])').waitFor();
   }
  }
  await page.locator('.nav-item[href="#pipeline"]').click();await page.reload();
  await page.locator('#pipeline:not([hidden]) #pipeline-steps li').nth(7).waitFor();
  const result={views,errors,pipelineSteps:8,pipelineReloadRestoresView:true,mutationRequests:requests.filter(r=>!['GET','HEAD'].includes(r.method)),exampleRequests:requests.filter(r=>r.url.endsWith('/api/examples')).length};
  fs.writeFileSync(path.join(out,'browser-check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  if(errors.length||views.some(v=>v.overflow||v.images!==5)||result.mutationRequests.length||result.exampleRequests!==2)throw new Error('Saved dashboard browser checks failed');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
