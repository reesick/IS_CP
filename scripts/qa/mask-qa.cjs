const {chromium}=require('../../.cache/ui-test/node_modules/playwright');
const assert=require('assert');
(async()=>{
const browser=await chromium.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});await page.goto('http://127.0.0.1:8000');
const image=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=800;c.height=400;c.getContext('2d').fillRect(0,0,800,400);return c.toDataURL().split(',')[1]});
await page.locator('#image-file').setInputFiles({name:'mask-ui-test.png',mimeType:'image/png',buffer:Buffer.from(image,'base64')});await page.locator('#workspace').waitFor();
const box=await page.locator('#mask-canvas').boundingBox();const point=(x,y)=>({x:box.x+x*box.width/512,y:box.y+y*box.height/512});let p=point(100,170);await page.mouse.move(p.x,p.y);await page.mouse.down();p=point(300,300);await page.mouse.move(p.x,p.y,{steps:10});await page.mouse.up();
await page.locator('#selection-info').filter({hasText:'200 × 130 region'}).waitFor();
await page.locator('#mask-mode').selectOption('background');
const responsePromise=page.waitForResponse(r=>r.url().endsWith('/mask')&&r.request().method()==='PUT');await page.locator('#protect-image').click();const response=await responsePromise;assert.equal(response.status(),200);const mask=await response.json();
const pixels=await page.evaluate(async id=>{const blob=await(await fetch('/api/v1/artifacts/'+id)).blob();const image=await createImageBitmap(blob);const c=document.createElement('canvas');c.width=c.height=512;const ctx=c.getContext('2d');ctx.drawImage(image,0,0);const value=(x,y)=>ctx.getImageData(x,y,1,1).data[0];return {padding:value(10,10),inside:value(150,200),outside:value(350,200),bottomPadding:value(150,450)};},mask.artifact_id);
assert.deepEqual(pixels,{padding:0,inside:0,outside:255,bottomPadding:0});
await page.locator('#protect-error').waitFor();page.once('dialog',d=>d.accept());await page.locator('#delete-asset').click();await page.locator('#upload-zone').waitFor();await browser.close();console.log('Pointer mapping and complemented mask pixels PASS',JSON.stringify(pixels));
})().catch(error=>{console.error(error);process.exitCode=1});
