// Optional local browser integration check. Uses actual API/worker/model calls.
const fs = require('fs');
const path = require('path');
const {createRequire} = require('module');
const root = path.resolve(__dirname, '..', '..');
const {chromium} = createRequire(path.join(root,'.cache/ui-test/package.json'))('playwright');
const output = path.join(root,'docs/screenshots');
const evidence = {purpose:'Synthetic smoke execution; not a defense efficacy benchmark',errors:[]};
const sleep = ms => new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
  const browser=await chromium.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const page=await context.newPage();
  page.on('pageerror',e=>evidence.errors.push(e.message));
  try {
    await page.goto('http://127.0.0.1:8000');
    await page.locator('#capability').filter({hasText:'GPU ready'}).waitFor({timeout:60000});
    await page.locator('#image-file').setInputFiles({name:'synthetic-smoke-input.png',mimeType:'image/png',buffer:fs.readFileSync(path.join(root,'data/ml-smoke/clean.png'))});
    await page.locator('#workspace').waitFor();
    await page.locator('#region-details').evaluate(el=>el.open=true);
    for(const [key,value] of Object.entries({x:160,y:160,width:193,height:193})) {
      await page.locator('#region-'+key).fill(String(value));
      await page.locator('#region-'+key).dispatchEvent('change');
    }
    await page.locator('#advanced-protection').evaluate(el=>el.open=true);
    await page.locator('#epsilon').selectOption('1');
    const responsePromise=page.waitForResponse(r=>r.url().endsWith('/protect')&&r.request().method()==='POST');
    await page.locator('#protect-image').click();
    const response=await responsePromise;
    if(response.status()!==202)throw new Error('Protection submission failed: '+await response.text());
    const submitted=await response.json();
    evidence.protection_job_id=submitted.id;
    async function snapshots(name) {
      for(const width of [1440,390]) {
        await page.setViewportSize({width,height:1000});
        await page.screenshot({path:path.join(output,`${width}-${name}.png`),fullPage:true});
      }
      await page.setViewportSize({width:1440,height:1000});
    }
    await page.locator('#job-status').waitFor();
    await snapshots('real-running');
    async function waitJob(id) {
      const started=Date.now();let previous='';
      while(Date.now()-started<30*60*1000) {
        const response=await context.request.get('http://127.0.0.1:8000/api/v1/jobs/'+id);
        const job=await response.json();
        const status=`${job.state}: ${job.stage} ${job.completed_steps??''}/${job.total_steps??''}`;
        if(status!==previous){console.log(status);previous=status;}
        if(!['queued','running'].includes(job.state))return job;
        await sleep(2000);
      }
      throw new Error('Timed out waiting for real job '+id);
    }
    evidence.protection=await waitJob(submitted.id);
    if(evidence.protection.state!=='succeeded'){
      await sleep(2000);await snapshots('real-protection-failed');
      throw new Error('Real protection state '+evidence.protection.state);
    }
    await page.locator('#protection-result').waitFor({timeout:10000});
    const downloaded=await context.request.get(await page.locator('#download-protected').getAttribute('href'));
    const downloadedBytes=await downloaded.body();
    if(downloaded.status()!==200 || downloadedBytes.subarray(0,8).toString('hex')!=='89504e470d0a1a0a')throw new Error('Protected PNG download failed');
    evidence.protected_download={status:200,bytes:downloadedBytes.length};
    await snapshots('real-protected-export');
    await page.locator('nav a[href="#attack-lab"]').click();
    await page.locator('#edit-prompt').fill('a shiny silver ball on the background');
    const editPromise=page.waitForResponse(r=>r.url().endsWith('/edit-tests')&&r.request().method()==='POST');
    await page.locator('#run-comparison').click();
    const editResponse=await editPromise;
    if(editResponse.status()!==202)throw new Error('Edit submission failed: '+await editResponse.text());
    const edit=await editResponse.json();
    evidence.edit_job_id=edit.id;
    evidence.edit=await waitJob(edit.id);
    if(evidence.edit.state!=='succeeded')throw new Error('Real paired edit failed: '+JSON.stringify(evidence.edit));
    await page.locator('#experiment-results').waitFor({timeout:15000});
    await page.locator('#comparison-grid img').first().waitFor();
    await page.evaluate(()=>Promise.all([...document.querySelectorAll('#comparison-grid img')].map(i=>i.decode())));
    await snapshots('real-paired-comparison');
    evidence.experiment=await (await context.request.get('http://127.0.0.1:8000/api/v1/experiments/'+evidence.edit.output.experiment_id)).json();
    evidence.browser_session_storage=await context.storageState();
    fs.mkdirSync(path.join(root,'data/browser-smoke'),{recursive:true});
    fs.writeFileSync(path.join(root,'data/browser-smoke/session.json'),JSON.stringify(evidence.browser_session_storage));
    delete evidence.browser_session_storage;
    evidence.passed=true;
  } catch(error) {
    evidence.failure=error.stack;console.error(error);process.exitCode=1;
  } finally {
    fs.writeFileSync(path.join(output,'gpu-browser-qa.json'),JSON.stringify(evidence,null,2));
    await browser.close();
  }
})();
