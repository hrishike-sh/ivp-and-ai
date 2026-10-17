const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('temporary unknown status continues polling until completion', () => {
  const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
  const start = source.indexOf('function showJob(');
  const end = source.indexOf('async function pollJob(', start);
  const elements = new Map();
  const pending = new Map();
  const saved = new Map();
  let serial = 0;
  const context = vm.createContext({
    state: {}, jobTimer: null,
    $: id => { if (!elements.has(id)) elements.set(id, {}); return elements.get(id); },
    showMotionResult: () => {}, links: () => '', pollJob: () => {},
    jobMessage: run => run.status.message || '',
    localStorage: {setItem: (k,v) => saved.set(k,v), getItem:k => saved.get(k), removeItem:k => saved.delete(k)},
    clearTimeout: id => pending.delete(id),
    setTimeout: fn => { const id = ++serial; pending.set(id, fn); return id; },
  });
  vm.runInContext(source.slice(start, end), context);
  for (const state of ['running', 'unknown', 'encoding', 'complete']) {
    context.showJob({id:'example', source:'traffic.mp4', status:{state}, downloads:[]});
    assert.equal(pending.size, state === 'complete' ? 0 : 1, state);
    assert.equal(saved.get('traffic-lab-active-job'), state === 'complete' ? undefined : 'example');
  }
  for (const state of ['cancelled', 'failed', 'interrupted']) {
    context.showJob({id:'example', source:'traffic.mp4', status:{state}, downloads:[]});
    assert.equal(pending.size, 0, state);
  }
});

test('saving a frame leaves the active video polling and identity intact', () => {
  const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
  const start = source.indexOf('function showFrameExport(');
  const end = source.indexOf('async function pollJob(', start);
  const card = {};
  const context = vm.createContext({state:{job:'video-in-progress'}, jobTimer:123,
    $: () => card, escapeHTML: s => s, links: () => 'frame download'});
  vm.runInContext(source.slice(start,end),context);
  context.showFrameExport({source:'traffic.mp4',status:{message:'Frame ready'},downloads:[]});
  assert.equal(context.state.job,'video-in-progress');
  assert.equal(context.jobTimer,123);
  assert.equal(card.hidden,false);
  assert.match(card.innerHTML,/frame download/);
});

test('progress reports measured frames and processing rate, not an early ETA', () => {
  const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
  const context=vm.createContext({});
  vm.runInContext(source.slice(source.indexOf('function jobMessage('),source.indexOf('function showJob(')),context);
  assert.equal(context.jobMessage({status:{message:'Starting',frames:1,fps:.1}}),'Starting · 1 frame processed');
  assert.equal(context.jobMessage({status:{message:'Processing',frames:120,fps:8.25},report:{info:{frame_count:600}}}),
    'Processing · 120 / 600 frames processed · 8.3 processing frames/s');
  assert.equal(context.jobMessage({status:{message:'Waiting'}}),'Waiting');
});

test('saved unfinished motion runs open status without treating settings as measurements', async () => {
  const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
  for (const status of ['queued','running','encoding','unknown','cancelled','failed','interrupted','complete']) {
    const elements=new Map(), errors=[], polled=[], rendered=[];
    let modalOpened=false;
    const run={id:'long-video',source:'workload.mp4',status:{state:status,message:'Job status'},downloads:[],
      report:{motion:status==='complete'?{timeline:[],line:{axis:'horizontal'}}:{axis:'horizontal',tracking_mode:'vehicles'}}};
    const context=vm.createContext({
      api:async()=>run, escapeHTML:s=>s, links:()=>'',
      $:id=>{
        if(id==='reuse-settings')return null;
        if(!elements.has(id))elements.set(id,{showModal:()=>{modalOpened=true;}});
        return elements.get(id);
      },
      motionSummary:motion=>{if(!motion.line)throw Error('Request settings are not a completed summary');rendered.push(motion);return 'Completed measurements';},
      showMotionResult:()=>{}, showJob:r=>polled.push(r.id), notify:e=>errors.push(e),
    });
    vm.runInContext(source.slice(source.indexOf('async function openRun('),source.indexOf('async function startReview(')),context);
    await context.openRun(run.id);
    assert.deepEqual(errors,[],status);
    assert.equal(modalOpened,true,status);
    assert.equal(rendered.length,status==='complete'?1:0,status);
    assert.equal(polled.length,['queued','running','encoding','unknown'].includes(status)?1:0,status);
  }
});

test('incident setup is opt-in and sends explicit conditions, scale flags and finite geometry',()=>{
  const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
  const values={'incident-start':'15','incident-end':'85','motion-position':'65','motion-axis':'horizontal',
    'incident-direction':'positive','incident-condition':'observe','incident-intervals':'0, 5, red\n5, 12, green',
    'incident-zone-rect':'15, 65, 85, 78','incident-approach':'15, 45, 85, 65','incident-limit':'30'};
  const elements=Object.fromEntries(Object.entries(values).map(([key,value])=>[key,{value}]));
  for(const name of ['enabled','line','zone','restricted','calibration-confirmed','real-time','synthetic'])elements['incident-'+name]={checked:false};
  const context=vm.createContext({$:id=>elements[id]});
  vm.runInContext(source.slice(source.indexOf('function incidentConfig('),source.indexOf('function paintIncidents(')),context);
  assert.equal(context.incidentConfig(),null);
  elements['incident-enabled'].checked=true;elements['incident-line'].checked=true;
  const config=JSON.parse(JSON.stringify(context.incidentConfig()));
  assert.deepEqual(config.line,[[.15,.65],[.85,.65]]);
  assert.equal(config.condition,'observe');assert.equal(config.zone_role,'observe');
  assert.equal(config.calibration_confirmed,false);assert.equal(config.real_time_confirmed,false);
  assert.equal(config.synthetic,false);assert.deepEqual(config.condition_intervals[1],{start:5,end:12,state:'green'});
  elements['incident-end'].value='10';assert.throws(()=>context.incidentConfig(),/line end/);
});

test('incident results distinguish candidates, neutral observations, withheld and synthetic evidence',()=>{
  const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
  const context=vm.createContext({escapeHTML:s=>String(s)});
  vm.runInContext(source.slice(source.indexOf('function incidentSummary('),source.indexOf('function motionSummary(')),context);
  assert.equal(context.incidentSummary(undefined),'');
  const html=context.incidentSummary({enabled:true,configuration:{synthetic:true},counts:{candidate:1,observation:2,withheld:3},
    events:[],event_count:6,thumbnail_policy:'First 40'});
  assert.match(html,/Synthetic incident review/);assert.match(html,/1 review candidates/);
  assert.match(html,/2 neutral observations/);assert.match(html,/3 withheld assessments/);
  assert.match(html,/Zero candidates does not establish/);
});
