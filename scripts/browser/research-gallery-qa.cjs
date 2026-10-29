const {chromium}=require('../../.cache/ui-test/node_modules/playwright');
const fs=require('fs');
const path=require('path');
const {pathToFileURL,fileURLToPath}=require('url');
(async()=>{
  const output=process.argv[2]?path.resolve(process.argv[2]):path.resolve(__dirname,'../../outputs/research-2026-10-28');
  const browser=await chromium.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true});
  const checks=[];
  try {
    for (const width of [1440,390]) {
      const page=await browser.newPage({viewport:{width,height:1000}});
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      await page.goto(pathToFileURL(path.join(output,'index.html')).href);
      await page.evaluate(()=>{for(const img of document.images)img.loading='eager';});
      await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete));
      const dimensions=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,images:document.images.length,broken:Array.from(document.images).filter(i=>!i.naturalWidth).map(i=>i.src)}));
      const links=await page.locator('a[href]').evaluateAll(nodes=>nodes.map(a=>a.href));
      dimensions.missingLinks=links.filter(url=>url.startsWith('file:')&&!fs.existsSync(fileURLToPath(url)));
      await page.screenshot({path:path.join(output,`gallery-${width}.png`)});
      checks.push({width,...dimensions,errors});await page.close();
    }
    fs.writeFileSync(path.join(output,'gallery-browser-check.json'),JSON.stringify(checks,null,2));
    console.log(JSON.stringify(checks));
    if(checks.some(c=>c.overflow||c.broken.length||c.errors.length||c.missingLinks.length))process.exitCode=1;
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
