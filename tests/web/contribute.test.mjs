import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const html = readFileSync(new URL('../../web/index.html', import.meta.url), 'utf8').replace('data-arena-app="true"', 'data-arena-app="test"');
const source = readFileSync(new URL('../../web/arena-contribute.js', import.meta.url), 'utf8').replace(/^export /gm, '');
function mount({email} = {}) {
  const dom = new JSDOM(html, {url:'http://arena.test/',runScripts:'outside-only',pretendToBeVisual:true});
  const w = dom.window, doc = w.document, drafts = [];
  w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open',''); };
  w.HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); this.dispatchEvent(new w.Event('close')); };
  w.eval(`${source}; window.initContributions=initArenaContributions; window.buildAccessRequest=buildAccessRequest;`);
  const options = {doc,compose:href=>drafts.push(href)};
  if (email !== undefined) options.accessEmail=email;
  const app = w.initContributions(options);
  return {dom,w,doc,drafts,app};
}

test('task contribution opens a native dialog before the explicit external PR link', () => {
  const {dom,doc,app,drafts}=mount();
  try {
    const trigger=doc.querySelector('#arena-growth [data-arena-contribution="task"]');
    assert.equal(trigger.tagName,'BUTTON');
    trigger.focus(); trigger.click();
    assert.equal(app.dialog.tagName,'DIALOG'); assert.equal(app.dialog.open,true);
    assert.equal(doc.activeElement.id,'arena-contribution-title');
    assert.equal(doc.getElementById('arena-contribution-title').textContent,'Submit a task');
    assert.equal(app.dialog.querySelectorAll('.contribution-steps li').length,3);
    assert.match(app.dialog.textContent,/candidate interface, evaluator, metric/);
    assert.equal(app.dialog.querySelector('.contribution-pr').href,'https://github.com/Doldrums/arena/compare?expand=1');
    assert.equal(app.dialog.querySelector('.contribution-pr').target,'_blank');
    assert.equal(drafts.length,0);
    app.dialog.querySelector('.contribution-close').click();
    assert.equal(app.dialog.open,false); assert.equal(doc.activeElement,trigger);
    assert.equal(doc.body.classList.contains('arena-contribution-open'),false);
  } finally {dom.window.close();}
});

test('system instructions distinguish private release registration, public identity and run access', () => {
  const {dom,doc,app}=mount();
  try {
    doc.querySelector('[data-arena-contribution="system"]').click();
    assert.equal(app.dialog.querySelectorAll('.contribution-steps li').length,4);
    assert.match(app.dialog.textContent,/private repository or container image/);
    assert.match(app.dialog.textContent,/private CI registration/);
    assert.match(app.dialog.textContent,/sciel 1\.0\.4/);
    assert.match(app.dialog.querySelector('.contribution-review-note').textContent,/being prepared/);
    assert.equal(app.dialog.querySelector('.contribution-pr').href,'https://github.com/Doldrums/arena/compare?expand=1');
    assert.match(app.dialog.textContent,/Registration is|Registering a system and requesting a run are separate/);
  } finally {dom.window.close();}
});

test('run access composes an encoded email to the configured recipient without sending or launching', () => {
  const {dom,w,doc,app,drafts}=mount();
  try {
    const before=w.location.href;
    doc.querySelector('[data-arena-contribution="system"]').click();
    app.dialog.querySelector('.contribution-access-link').click();
    assert.equal(app.dialog.querySelector('.contribution-overview').hidden,true);
    assert.equal(app.dialog.querySelector('.contribution-request').hidden,false);
    const form=app.dialog.querySelector('form');
    assert.equal(doc.activeElement,form.elements.namedItem('name'));
    const values={name:'A Researcher',email:'researcher@example.edu',affiliation:'Lab & Group',system:'sciel 1.0.4',research:'Compare memory updates\nTasks: packing & optimization; budget: 10 runs.'};
    for (const [key,value] of Object.entries(values)) form.elements.namedItem(key).value=value;
    form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
    assert.equal(drafts.length,1);
    const url=new URL(drafts[0]);
    assert.equal(url.protocol,'mailto:'); assert.equal(url.pathname,'arina.kharlamova@mbzuai.ac.ae');
    assert.match(url.searchParams.get('subject'),/sciel 1\.0\.4/);
    assert.match(url.searchParams.get('body'),/Lab & Group/);
    assert.ok(url.searchParams.get('body').includes(values.research));
    assert.match(url.searchParams.get('body'),/Contribution: System/);
    assert.equal(w.location.href,before);
    assert.match(app.dialog.querySelector('[role="status"]').textContent,/Review and send it from your email app/);
    app.dialog.querySelector('.contribution-back').click();
    assert.equal(app.dialog.querySelector('.contribution-overview').hidden,false);
    assert.equal(doc.activeElement,app.dialog.querySelector('.contribution-access-link'));
  } finally {dom.window.close();}
});

test('invalid or unconfigured access requests never compose email', () => {
  const {dom,w,doc,app,drafts}=mount({email:''});
  try {
    doc.querySelector('[data-arena-contribution="task"]').click();
    app.dialog.querySelector('.contribution-access-link').click();
    const form=app.dialog.querySelector('form');
    form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
    assert.equal(drafts.length,0);
    for (const [key,value] of Object.entries({name:'Researcher',email:'a@example.edu',research:'A controlled study'})) form.elements.namedItem(key).value=value;
    form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
    assert.equal(drafts.length,0);
    assert.match(app.dialog.querySelector('[role="status"]').textContent,/not configured/);
  } finally {dom.window.close();}
});

test('dynamic header mode and backdrop dismissal preserve focus and leave catalog location unchanged', () => {
  const {dom,w,doc,app}=mount();
  try {
    const trigger=doc.getElementById('arena-contribute');
    trigger.dataset.arenaContribution='system';
    trigger.click();
    assert.equal(doc.getElementById('arena-contribution-title').textContent,'Submit a system');
    assert.equal(w.initContributions({doc}),null);
    app.dialog.getBoundingClientRect=()=>({left:10,right:300,top:10,bottom:500});
    app.dialog.dispatchEvent(new w.MouseEvent('click',{bubbles:true,clientX:5,clientY:5}));
    assert.equal(app.dialog.open,false); assert.equal(doc.activeElement,trigger);
    assert.equal(w.location.href,'http://arena.test/');
    app.destroy();trigger.click();
    assert.equal(doc.getElementById('arena-contribution-dialog'),null);
  } finally {dom.window.close();}
});
