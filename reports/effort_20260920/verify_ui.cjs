const fs=require('fs');
const path=require('path');
const puppeteer=require('/Users/amoriodi/node_modules/puppeteer');
const meta=JSON.parse(fs.readFileSync('/tmp/arena-effort-qa-server.json','utf8'));
const base='http://127.0.0.1:'+meta.port;
const out=__dirname;
(async()=>{
 const report={checked_at:new Date().toISOString(),base,scope:'Read-only ephemeral observer of saved live-run artifacts; no experiment execution or launch',pages:[],errors:[]};
 const browser=await puppeteer.launch({headless:true,executablePath:'/Users/amoriodi/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell',args:['--no-sandbox']});
 try{
  const data=await(await fetch(base+'/api/runs')).json();
  for(const [label,part] of [['circle','circle_opus5'],['heilbronn','heilbronn_opus5'],['oracle','oracle_opus5']]){
   const run=data.runs.find(r=>r.path.includes(part));if(!run)throw Error('Missing root '+part);
   const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(String(e)));
   page.on('response',r=>{if(r.status()>=400)report.errors.push(r.status()+' '+r.url());});
   await page.setViewport({width:1440,height:1100});
   await page.goto(base+'/experiments?run='+run.id,{waitUntil:'domcontentloaded'});
   await page.waitForSelector('.effort-scopes',{timeout:30000});
   await page.waitForFunction(()=>document.querySelector('#run-path').textContent.includes('_v32'));
   await page.click('#follow-button');
   if(label==='circle'){
    await page.$eval('.benchmark-disclosure',el=>el.open=true);
    await page.$$eval('.benchmark-current .effort-models',els=>els.forEach(el=>el.open=true));
   }
   const snapshot=await(await fetch(base+'/api/runs/'+run.id)).json();
   const inspect=()=>page.evaluate(()=>({title:document.title,viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,
    scopes:[...document.querySelectorAll('.effort-scopes section')].map(e=>e.textContent),current:document.querySelector('.benchmark-current')?.textContent,
    gaps:document.querySelector('#best-score-comparison')?.textContent,clipped: [...document.querySelectorAll('.effort-facts,.benchmark-reference-gap')].filter(el=>el.clientWidth>0&&el.scrollWidth>el.clientWidth+1).map(el=>el.className),tableScrollable:(()=>{const t=document.querySelector('.benchmark-table');return t?{client:t.clientWidth,scroll:t.scrollWidth}:null;})()}));
   const desktop=await inspect();await page.screenshot({path:path.join(out,label+'-desktop.png'),fullPage:false});
   if(label==='circle'){
    await page.$eval('.benchmark-current',el=>el.scrollIntoView({block:'center'}));
    await page.screenshot({path:path.join(out,'circle-current-row.png'),fullPage:false});
    await page.$$eval('.benchmark-table tr',rows=>{const row=rows.find(r=>r.textContent.includes('ShinkaEvolve'));row?.querySelectorAll('details').forEach(e=>e.open=true);row?.scrollIntoView({block:'center'});});
    await page.screenshot({path:path.join(out,'circle-published-models.png'),fullPage:false});
   }
   await page.setViewport({width:390,height:844});await page.evaluate(()=>scrollTo(0,0));
   const mobile=await inspect();await page.screenshot({path:path.join(out,label+'-mobile.png'),fullPage:false});
   if(label==='circle'){
    await page.$eval('.effort-scopes',el=>el.scrollIntoView({block:'start'}));
    await page.screenshot({path:path.join(out,'circle-mobile-effort.png'),fullPage:false});
   }
   report.pages.push({label,run_id:run.id,path:run.path,desktop,mobile,effort:snapshot.effort,metric:snapshot.stats.best_metric_display});
   await page.close();
  }
  report.pass=report.errors.length===0&&report.pages.every(p=>p.desktop.documentWidth<=p.desktop.viewport+1&&p.mobile.documentWidth<=p.mobile.viewport+1&&!p.desktop.clipped.length&&!p.mobile.clipped.length)&&report.pages[0].desktop.current.includes('p29')&&report.pages[0].desktop.gaps.includes('Best AI search');
 }catch(e){report.errors.push(String(e));report.pass=false;}finally{await browser.close();fs.writeFileSync(path.join(out,'live-ui.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({pass:report.pass,pages:report.pages.length,errors:report.errors}));}
})().catch(e=>{console.error(e);process.exitCode=1;});
