import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const source=readFileSync(new URL('../../web/packings.js',import.meta.url),'utf8').replace(/^export /gm,'');
const pause=()=>new Promise(resolve=>setTimeout(resolve,5));
async function until(predicate){for(let i=0;i<400;i++){if(predicate())return;await pause();}assert.fail('Gallery did not update');}
function mount(){const dom=new JSDOM('<main id="root"></main>',{runScripts:'outside-only',pretendToBeVisual:true,url:'https://example.test/'});const w=dom.window;w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'));};w.eval('{'+source+';Object.assign(window,{renderPackings,suspendPackings,destroyPackings});}');return {dom,w,root:w.document.getElementById('root')};}
const item=(id='e1',extra={})=>({id,program_id:'p'+id,evaluation_id:'evaluation:'+id,island_id:0,iteration:3,timestamp:'2026-09-20T09:00:00Z',score:.123456789123,valid:true,source_sha256:'a'.repeat(64),centers:[[.2,.3],[.7,.8]],radii:[.1,.12],...extra});
const page=(items,extra={})=>({schema:'sciel-packings/1',supported:true,total:items.length,available:items.length,unavailable:0,offset:0,limit:120,has_more:false,content_version:'saved1',islands:[0,2],items,...extra});
const opts=(fetchJSON,extra={})=>({runId:'run one',identity:'science',version:'v1',fetchJSON,...extra});

test('packing boards override shared button icon sizing and keep detail geometry full width',async()=>{
 const {dom,w,root}=mount();try{
 for(const file of ['style.css','packings.css']){const style=w.document.createElement('style');style.textContent=readFileSync(new URL('../../web/'+file,import.meta.url),'utf8');w.document.head.append(style);}
 w.renderPackings(root,opts(async()=>page([item()])));await until(()=>root.querySelector('.pg-tile'));
 const tile=root.querySelector('.pg-tile'),small=tile.querySelector('svg'),smallStyle=w.getComputedStyle(small);
 assert.equal(smallStyle.width,'100%');assert.equal(smallStyle.height,'auto');assert.equal(smallStyle.aspectRatio,'1');assert.equal(smallStyle.stroke,'none');
 assert.equal(small.querySelector('circle').getAttribute('stroke'),'#61738d');assert.equal(small.querySelector('circle').getAttribute('stroke-width'),'0.0025');
 tile.click();const largeStyle=w.getComputedStyle(root.querySelector('.pg-board-large'));
 assert.equal(largeStyle.width,'100%');assert.equal(largeStyle.height,'auto');assert.equal(largeStyle.maxWidth,'none');assert.equal(largeStyle.stroke,'none');
 }finally{dom.window.close();}
});

test('renders exact saved geometry and native score, expands metadata, and links the actual program',async()=>{
 const {dom,w,root}=mount();try{let selected;const saved=item('e1');w.renderPackings(root,opts(async()=>page([saved]),{onProgram:id=>{selected=id;}}));await until(()=>root.querySelector('.pg-tile'));
 const tile=root.querySelector('.pg-tile');assert.match(tile.textContent,/0\.123456789/);assert.match(tile.textContent,/Island 0/);const circles=tile.querySelectorAll('circle');assert.equal(circles.length,2);assert.equal(circles[0].getAttribute('cx'),String(saved.centers[0][0]));assert.equal(circles[0].getAttribute('cy'),String(1-saved.centers[0][1]));assert.equal(circles[0].getAttribute('r'),String(saved.radii[0]));
 tile.click();assert.equal(root.querySelector('dialog').open,true);assert.match(root.querySelector('.pg-detail').textContent,/09:00:00 UTC/);assert.match(root.querySelector('.pg-detail').textContent,/Valid under the recorded evaluator/);assert.deepEqual(JSON.parse(root.querySelector('.pg-exact pre').textContent),{centers:saved.centers,radii:saved.radii});assert.equal(root.querySelector('.pg-exact').open,false);root.querySelector('.pg-code').click();assert.equal(selected,'pe1');assert.equal(root.querySelector('dialog').open,false);
 }finally{dom.window.close();}
});

test('all history remains accessible beyond 600 layouts through load more',async()=>{
 const {dom,w,root}=mount();try{const rows=Array.from({length:721},(_,i)=>item('e'+i)),requests=[];w.renderPackings(root,opts(async path=>{const query=new URL(path,'https://test').searchParams,offset=Number(query.get('offset'));requests.push(offset);return page(rows.slice(offset,offset+120),{total:rows.length,available:rows.length,offset,has_more:offset+120<rows.length});}));await until(()=>root.querySelectorAll('.pg-tile').length===120);
 for(let n=2;n<=7;n++){root.querySelector('.pg-more').click();await until(()=>root.querySelectorAll('.pg-tile').length===Math.min(n*120,721));}
 assert.deepEqual(requests,[0,120,240,360,480,600,720]);assert.equal(root.querySelector('.pg-more').hidden,true);assert.match(root.querySelector('.pg-count').textContent,/721 of 721/);
 }finally{dom.window.close();}
});

test('search, island, and sort use encoded server filters without a client history cap',async()=>{
 const {dom,w,root}=mount();try{const calls=[];w.renderPackings(root,opts(async path=>{calls.push(new URL(path,'https://test'));return page([item()]);}));await until(()=>root.querySelector('.pg-tile'));
 const search=root.querySelector('.pg-search');search.value='p1 & <layout>';search.dispatchEvent(new w.Event('input'));await until(()=>calls.length===2);assert.equal(calls[1].searchParams.get('q'),'p1 & <layout>');assert.match(calls[1].pathname,/run%20one\/packings$/);
 const island=root.querySelector('.pg-island');island.value='2';island.dispatchEvent(new w.Event('change'));await until(()=>calls.length===3);assert.equal(calls[2].searchParams.get('island'),'2');const sort=root.querySelector('.pg-sort');sort.value='oldest';sort.dispatchEvent(new w.Event('change'));await until(()=>calls.length===4);assert.equal(calls[3].searchParams.get('sort'),'oldest');assert.equal(calls[3].searchParams.get('offset'),'0');
 }finally{dom.window.close();}
});

test('valid zero stays measured; invalid penalty zero is not presented as a native score',async()=>{
 const {dom,w,root}=mount();try{w.renderPackings(root,opts(async()=>page([item('valid',{score:0}),item('invalid',{score:0,valid:false,program_id:null,radii:[-.1,.12]})],{unavailable:4})));await until(()=>root.querySelectorAll('.pg-tile').length===2);const [valid,invalid]=root.querySelectorAll('.pg-tile');assert.match(valid.textContent,/0\.000000000/);assert.match(invalid.textContent,/Invalid layout/);assert.doesNotMatch(invalid.textContent,/0\.000000000/);assert.equal(invalid.querySelectorAll('circle').length,1);invalid.click();assert.match(root.querySelector('.pg-detail').textContent,/Negative radii cannot be drawn/);assert.equal(root.querySelector('.pg-code').disabled,true);assert.match(root.querySelector('.pg-notice').textContent,/4 evaluations have no available verified layout/);
 }finally{dom.window.close();}
});

test('unsupported, empty, failed, and malformed data states remain distinct and safe',async()=>{
 const {dom,w,root}=mount();try{w.renderPackings(root,opts(async()=>page([],{supported:false,supported_reason:'Task <img src=x> has no saved geometry'})));await until(()=>!root.querySelector('.pg-empty').hidden);assert.match(root.textContent,/not supported/);assert.match(root.textContent,/<img src=x>/);assert.equal(root.querySelector('img'),null);
 w.renderPackings(root,opts(async()=>page([]),{runId:'empty'}));await until(()=>root.textContent.includes('No saved packing layouts yet'));
 w.renderPackings(root,opts(async()=>{throw new Error('fixture unavailable');},{runId:'failed'}));await until(()=>!root.querySelector('.pg-error').hidden);assert.match(root.textContent,/fixture unavailable/);assert.doesNotMatch(root.textContent,/No saved packing layouts yet/);
 w.renderPackings(root,opts(async()=>page([item('<script>literal</script>'),item('bad',{centers:[[NaN,0]]})]),{runId:'malformed'}));await until(()=>root.querySelector('.pg-tile'));assert.equal(root.querySelectorAll('.pg-tile').length,1);assert.equal(root.querySelector('script'),null);assert.match(root.querySelector('.pg-notice').textContent,/1 returned layouts could not be drawn/);
 }finally{dom.window.close();}
});

test('run switches abort in-flight requests and discard late old responses',async()=>{
 const {dom,w,root}=mount();try{let resolve,signal;w.renderPackings(root,opts((_,options)=>{signal=options.signal;return new Promise(r=>{resolve=r;});}));await until(()=>resolve);w.renderPackings(root,opts(async()=>page([item('new')]),{runId:'new'}));assert.equal(signal.aborted,true);await until(()=>root.querySelector('[data-packing-id=new]'));resolve(page([item('old')]));await pause();assert.equal(root.querySelector('[data-packing-id=old]'),null);
 }finally{dom.window.close();}
});

test('polling retains selection, open coordinates, nodes and scroll; same content version does not fetch',async()=>{
 const {dom,w,root}=mount();try{let calls=0,rows=[item()];const options=opts(async()=>{calls++;return page(rows,{content_version:String(calls)});});w.renderPackings(root,options);await until(()=>root.querySelector('.pg-tile'));const tile=root.querySelector('.pg-tile');tile.click();const exact=root.querySelector('.pg-exact'),pre=exact.querySelector('pre');exact.open=true;pre.scrollTop=83;root.scrollTop=77;w.renderPackings(root,options);await pause();assert.equal(calls,1);
 rows=[item(),item('e2')];w.renderPackings(root,{...options,version:'v2'});await until(()=>root.querySelectorAll('.pg-tile').length===2);assert.strictEqual(root.querySelector('.pg-tile'),tile);assert.strictEqual(root.querySelector('.pg-exact'),exact);assert.equal(exact.open,true);assert.equal(pre.scrollTop,83);assert.equal(root.scrollTop,77);assert.equal(tile.getAttribute('aria-pressed'),'true');assert.equal(root.querySelector('dialog').open,true);
 }finally{dom.window.close();}
});

test('suspend aborts work without dropping filters; resume loads changed content; destroy discards late work',async()=>{
 const {dom,w,root}=mount();try{let calls=0,resolve,signal;const fetchJSON=(_,options)=>{calls++;if(calls===1)return Promise.resolve(page([item()]));signal=options.signal;return new Promise(r=>{resolve=r;});};const options=opts(fetchJSON);w.renderPackings(root,options);await until(()=>root.querySelector('.pg-tile'));const sort=root.querySelector('.pg-sort');sort.value='newest';sort.dispatchEvent(new w.Event('change'));await until(()=>resolve);w.suspendPackings(root);assert.equal(signal.aborted,true);resolve(page([item('stale')]));await pause();assert.equal(root.querySelector('[data-packing-id=stale]'),null);
 w.renderPackings(root,opts(async()=>page([item('latest')]),{version:'v2'}));await until(()=>root.querySelector('[data-packing-id=latest]'));assert.equal(root.querySelector('.pg-sort').value,'newest');let late;w.renderPackings(root,opts(()=>new Promise(r=>{late=r;}),{version:'v3'}));await until(()=>late);w.destroyPackings(root);late(page([item('after-destroy')]));await pause();assert.equal(root.children.length,0);
 }finally{dom.window.close();}
});

test('changed history between pages restarts from zero instead of skipping or duplicating offsets',async()=>{
 const {dom,w,root}=mount();try{const calls=[],original=Array.from({length:120},(_,i)=>item('old'+i));w.renderPackings(root,opts(async path=>{const offset=Number(new URL(path,'https://test').searchParams.get('offset'));calls.push(offset);if(calls.length===1)return page(original,{total:121,has_more:true});if(offset===0)return page([item('inserted'),...original.slice(0,119)],{total:122,has_more:true,content_version:'saved2'});return page([original[119],item('last')],{offset:120,total:122,content_version:'saved2'});}));await until(()=>root.querySelectorAll('.pg-tile').length===120);root.querySelector('.pg-more').click();await until(()=>root.querySelectorAll('.pg-tile').length===122);assert.deepEqual(calls,[0,120,0,120]);assert.equal(root.querySelector('.pg-tile').dataset.packingId,'inserted');assert.match(root.querySelector('.pg-count').textContent,/122 of 122/);
 }finally{dom.window.close();}
});
