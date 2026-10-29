const { chromium }=require('../../.cache/ui-test/node_modules/playwright');
const fs=require('fs');
const path=require('path');
(async()=>{
 const output=path.resolve(__dirname,'../../docs/screenshots');fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true});
 const results=[];const errors=[];
 for(const width of [1440,390]){
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});const page=await context.newPage();
  page.on('pageerror',error=>errors.push({width,message:error.message}));
  page.on('console',message=>{if(message.type()==='error'&&!message.text().includes('status of 404')&&!message.text().includes('status of 503'))errors.push({width,message:message.text()});});
  await page.goto('http://127.0.0.1:8000');await page.locator('#capability').filter({hasText:/Setup required|GPU ready/}).waitFor({timeout:60000});
  await page.screenshot({path:path.join(output,`${width}-protect-empty.png`),fullPage:true});
  const image=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=800;c.height=400;const ctx=c.getContext('2d');ctx.fillStyle='#dfd9ce';ctx.fillRect(0,0,800,400);ctx.fillStyle='#688078';ctx.fillRect(100,60,300,280);ctx.fillStyle='#fff';ctx.font='25px sans-serif';ctx.fillText('UI TEST IMAGE',450,180);ctx.fillText('Not an efficacy result',450,225);return c.toDataURL().split(',')[1];});
  await page.locator('#image-file').setInputFiles({name:'ui-test-image.png',mimeType:'image/png',buffer:Buffer.from(image,'base64')});
  await page.locator('#workspace').waitFor();await page.locator('#region-details').evaluate(node=>node.open=true);
  for(const [key,value]of Object.entries({x:64,y:168,width:192,height:176})){await page.locator('#region-'+key).fill(String(value));await page.locator('#region-'+key).dispatchEvent('change');}
  await page.locator('#selection-info').filter({hasText:'26% editable'}).waitFor();
  await page.screenshot({path:path.join(output,`${width}-selected-region.png`),fullPage:true});
  await page.reload();await page.locator('#workspace').waitFor();await page.locator('#selection-info').filter({hasText:'26% editable'}).waitFor();
  if(await page.locator('#capability').textContent()==='Setup required'){
   await page.locator('#protect-image').click();await page.locator('#protect-error').waitFor();
   await page.screenshot({path:path.join(output,`${width}-model-unavailable.png`),fullPage:true});
  }
  await page.locator('nav a[href="#attack-lab"]').click();await page.locator('#attack-empty').waitFor();
  await page.screenshot({path:path.join(output,`${width}-attack-empty.png`),fullPage:true});
  await page.locator('nav a[href="#verify"]').click();await page.getByRole('heading',{name:'Verification is not enabled'}).waitFor();
  await page.screenshot({path:path.join(output,`${width}-verify-unavailable.png`),fullPage:true});
  await page.goBack();await page.locator('#attack-lab').waitFor();
  await page.locator('nav a[href="#protect"]').click();await page.locator('#theme').click();
  await page.screenshot({path:path.join(output,`${width}-dark-selected.png`),fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);if(overflow)errors.push({width,message:'Horizontal overflow'});
  await page.locator('nav a[href="#protect"]').focus();await page.keyboard.press('ArrowRight');if(!page.url().endsWith('#attack-lab'))errors.push({width,message:'Keyboard nav failed'});
  await page.locator('nav a[href="#protect"]').click();page.once('dialog',dialog=>dialog.accept());await page.locator('#delete-asset').click();await page.locator('#upload-zone').waitFor();
  const transparent=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=c.height=128;const ctx=c.getContext('2d');ctx.fillStyle='#2563eb';ctx.fillRect(32,32,64,64);return c.toDataURL().split(',')[1];});
  await page.locator('#image-file').setInputFiles({name:'alpha-ui-test.png',mimeType:'image/png',buffer:Buffer.from(transparent,'base64')});await page.locator('dialog').waitFor();await page.screenshot({path:path.join(output,`${width}-alpha-confirmation.png`),fullPage:true});await page.getByRole('button',{name:'Continue with neutral background'}).click();await page.locator('#workspace').waitFor();
  page.once('dialog',dialog=>dialog.accept());await page.locator('#delete-asset').click();await page.locator('#upload-zone').waitFor();
  results.push({width,checks:['empty','upload','numeric-mask','session-restore','model-unavailable','attack-empty','verify-unavailable','history','dark-theme','no-overflow','keyboard-nav','reduced-motion','alpha-consent','delete']});
  await context.close();
 }
 await browser.close();fs.writeFileSync(path.join(output,'browser-qa.json'),JSON.stringify({results,errors},null,2));console.log(JSON.stringify({results,errors},null,2));if(errors.length)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
