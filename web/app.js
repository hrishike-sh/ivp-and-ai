'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="traffic-token"]').content;
const state = {config:null, settings:null, media:null, preview:null, view:'stages', mode:'automatic', area:'ivp', step:1, undo:[], redo:[], revision:0, rendering:false, pending:false, region:null, regionTool:false, job:null, runs:[], review:null};
const copy = value => JSON.parse(JSON.stringify(value));
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let toastTimer, previewTimer, jobTimer, reviewTimer;
function notify(message, error=false){ clearTimeout(toastTimer); $('notification').textContent=message; $('notification').className=error?'error':''; $('notification').hidden=false; toastTimer=setTimeout(()=>$('notification').hidden=true,error?10000:4500); }
async function performApi(path, data){ const response=await fetch(path, data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Traffic-Token':token},body:JSON.stringify(data)}); let value; try{value=await response.json();}catch{throw Error('The local server did not respond. Restart Traffic Lab and reload.');} if(!response.ok) throw Error(value.error||'Request failed.'); return value; }
let apiQueue=Promise.resolve();
function api(path,data){const task=apiQueue.then(()=>performApi(path,data));apiQueue=task.catch(()=>{});return task;}
function payload(){return {media:state.media?.id,timestamp:Number($('timestamp').value)||0,settings:copy(state.settings),mode:state.mode};}
function masks(){return [...document.querySelectorAll('#mask-list input:checked')].map(e=>e.value);}
function busy(message,error=false){$('preview-state').textContent=message;$('preview-state').classList.toggle('error',error);}
function actions(){motionActions();surveyActions();const ready=!!state.preview&&!state.rendering&&!state.pending; for(const id of ['export-frame','export-video','analyse','region-tool']) $(id).disabled=!ready; $('review').disabled=!state.media||!!state.review; $('undo').disabled=!state.undo.length;$('redo').disabled=!state.redo.length;}

const groups = [
 ['Light & colour',true,[
  ['exposure','Exposure','range',-3,3,.1,'stops','Multiply pixel values by 2 to the power of the exposure. Positive values can clip highlights.'],
  ['gamma','Gamma','range',.2,4,.1,'','Above 1 brightens midtones. This is a nonlinear intensity transform.'],
  ['clahe','CLAHE on colour export','checkbox'],
  ['clip_limit','CLAHE strength','range',1,8,.5,'','Limits local histogram amplification; excessive strength can reveal noise.'],
  ['stretch','Contrast clipping','range',0,10,.5,'%','Percentile stretch. 0 disables it; larger values discard more extreme tones.'],
  ['white_balance','White balance','range',0,1,.05,'','Gray-world correction strength. Assumes average scene colour is neutral; coloured scenes can be distorted.'],
  ['saturation','Saturation','range',0,2,.1,'','Adjust HSV saturation. 0 removes colour; 1 preserves it.']]],
 ['Noise & detail',false,[['denoise','Denoise filter','select',['Off','Gaussian','Median','Bilateral']],['kernel','Filter size','select',[3,5,7,9]],['sharpen','Unsharp masking','range',0,2,.1,'','Boosts existing edges. It cannot recover missing or motion-blurred information.']]],
 ['Edges & morphology',false,[['canny_low','Canny lower threshold','range',0,250,1],['canny_high','Canny upper threshold','range',1,255,1],['threshold_mode','Threshold method','select',['Otsu','Adaptive','Fixed']],['threshold_value','Binary threshold','range',0,255,1],['morphology','Morphology','select',['Off','Open','Close','Open + close']],['morph_kernel','Morphology kernel','select',[3,5,7,9]],['line_length','Minimum line length','range',5,300,1,'px']]],
 ['Colour isolation',false,[['hue_center','Hue centre','range',0,179,1,'','OpenCV hue scale: red 0, amber 20, green 60. Hue wraps at 179.'],['hue_tolerance','Hue tolerance','range',1,45,1],['saturation_min','Minimum saturation','range',0,255,1],['value_min','Minimum value','range',0,255,1]]],
 ['Size & video',false,[['max_width','Maximum output width','select',[0,640,960,1280,1920]],['scene_threshold','Scene change threshold','range',.05,1,.05,'','Lower values are more sensitive, including to lighting changes.']]]
];
function makeControls(){
 $('controls').innerHTML=groups.map(([title,open,controls])=>`<details ${open?'open':''}><summary>${title}</summary>${controls.map(([key,label,type,min,max,step,unit='',hint=''])=>{
 const id='setting-'+key; let control;
 if(type==='select') control=`<select id="${id}" data-setting="${key}">${min.map(v=>`<option value="${v}">${key==='max_width'?(v?v+' px':'Original size'):v}</option>`).join('')}</select>`;
 else if(type==='checkbox') control=`<input id="${id}" data-setting="${key}" type="checkbox">`;
 else control=`<input id="${id}" data-setting="${key}" type="range" min="${min}" max="${max}" step="${step}">`;
 return `<div class="control"><div class="control-top"><label for="${id}">${label}</label>${type==='range'?`<output id="value-${key}"></output>`:''}</div>${control}${hint?`<small>${hint}</small>`:''}</div>`;
 }).join('')}</details>`).join('');
 for(const element of document.querySelectorAll('[data-setting]')){
  element.addEventListener('input',()=>{const key=element.dataset.setting;let value=element.type==='checkbox'?element.checked:typeof state.config.defaults[key]==='number'?Number(element.value):element.value; record();state.settings[key]=value;$('settings-label').textContent='Custom'; sync();schedule();});
 }
 sync();
}
function sync(){
 const matching=Object.entries(state.config.presets).find(([,preset])=>Object.keys(preset).every(key=>preset[key]===state.settings[key]));$('preset').value=matching?matching[0]:'';
 for(const element of document.querySelectorAll('[data-setting]')){const key=element.dataset.setting; if(element.type==='checkbox')element.checked=state.settings[key]; else element.value=state.settings[key];if($('value-'+key))$('value-'+key).textContent=Number(state.settings[key]).toFixed(Number(element.step)<1?2:0);}
 $('setting-clip_limit').disabled=false;$('setting-threshold_value').disabled=state.settings.threshold_mode!=='Fixed';actions();
}
function record(){state.undo.push(copy(state.settings));if(state.undo.length>40)state.undo.shift();state.redo=[];}
function changeSettings(settings,label){setMode('manual',false);record();state.settings=copy(settings);$('settings-label').textContent=label;sync();schedule();}
function schedule(){clearSurvey();state.revision++;state.pending=!!state.media;actions();clearTimeout(previewTimer);if(state.media){busy('Adjusting…');previewTimer=setTimeout(renderPreview,300);}}
async function renderPreview(){
 if(state.rendering||!state.media)return; state.rendering=true;state.pending=false;const revision=state.revision;const request=payload();busy('Processing…');actions();
 try{const preview=await api('/api/preview',request);if(revision===state.revision){state.preview=preview;if(state.mode==='automatic'){state.settings=copy(preview.settings);sync();}paint();busy('Preview ready');if(state.region)measureRegion();}}
 catch(error){if(revision===state.revision){notify(error.message,true);busy('Preview out of date',true);state.preview=null;}}
 finally{state.rendering=false;actions();if(state.pending)renderPreview();}
}
async function openMedia(media, timestamp=0){
 clearIncidents();
 clearTarget();clearCalibration();clearSurvey();$('motion-use-roi').checked=false;state.revision++;state.media=media;state.preview=null;state.region=null;state.regionTool=false;$('region-box').hidden=true;$('frame').classList.remove('selecting');$('region-tool').setAttribute('aria-pressed','false');$('region-stats').innerHTML='<p class="hint">No region selected.</p>';$('review-output').textContent='';
 $('media-name').textContent=media.name;$('media-meta').textContent=`${media.width} × ${media.height} · ${(media.size_bytes/1048576).toFixed(1)} MB`+(media.kind==='video'?` · ${media.duration.toFixed(2)} s · ${media.fps.toFixed(2)} fps · ${media.has_audio?'Audio present':'No audio'}`:' · RGB');
 const video=media.kind==='video';$('video-timeline').hidden=!video;$('export-video').hidden=!video;$('timestamp').max=Math.max(0,Number(media.duration||0)-.001);$('timestamp').value=Math.min(timestamp,Number($('timestamp').max));$('time-label').textContent=Number($('timestamp').value).toFixed(2)+' s';$('export-frame').textContent=video?'Save frame + IVP stages ↓':'Save image + IVP stages ↓';$('analyse').textContent=video?'Analyse full video':'Analyse image';
 $('export-note').textContent=video?'The stage ZIP covers this frame. Full video export is enhanced colour with timed audio and sampled feature masks; automatic settings stay fixed from frame zero.':'Save every IVP stage, its explanation, colour output and measurements.';
 if(media.name==='india-city.mp4'){state.region=[.04,.28,.94,.98];$('motion-use-roi').checked=true;$('motion-axis').value='horizontal';$('motion-position').value='70';drawRegion();}else if(media.name.startsWith('india-')){state.region=[0,.4,1,.98];$('motion-use-roi').checked=true;$('motion-axis').value=media.name.includes('overhead')?'horizontal':'vertical';$('motion-position').value=media.name.includes('overhead')?'65':'50';drawRegion();} $('mask-list').innerHTML='';state.pending=true;actions();await renderPreview();
}
async function sample(name){if(!name)return;try{busy('Opening…');await openMedia(await api('/api/sample',{name}));}catch(e){notify(e.message,true);busy('Could not open',true);}}
async function upload(file){if(!file)return;if(file.size>1024**3){notify('Choose a file smaller than 1 GB.',true);return;}busy('Uploading…');try{
 const result=await new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('POST','/api/upload?name='+encodeURIComponent(file.name));xhr.setRequestHeader('X-Traffic-Token',token);xhr.upload.onprogress=e=>{if(e.lengthComputable)busy(`Uploading ${Math.round(e.loaded/e.total*100)}%`);};xhr.onload=()=>{try{const value=JSON.parse(xhr.responseText);xhr.status===200?resolve(value):reject(Error(value.error));}catch{reject(Error('Upload failed. Check the local server.'));}};xhr.onerror=()=>reject(Error('Upload interrupted. Please retry.'));xhr.send(file);});$('sample').value='';await openMedia(result);
 }catch(e){notify(e.message,true);busy('Upload failed',true);}finally{$('upload').value='';}}

const concepts={
 'Grayscale':'Luminance combines RGB channels into a single intensity plane. Colour information is removed.',
 'Hue':'Hue from the original colour frame, scaled for display. This is a channel visualization, not natural colour.',
 'Saturation':'Saturation measures colourfulness in the original HSV frame.', 'Value':'HSV value is the largest original RGB channel value.',
 'Colour mask':'Hue, saturation and value thresholds on the original frame isolate a colour range. A red patch alone is not a traffic signal.',
 'White marking mask':'Low saturation and high value isolate white regions. Buildings and reflections can also appear in this mask.',
 'Edges':'Canny uses intensity gradients and two thresholds to connect strong edges with nearby weaker ones.',
 'Threshold':'Binarization separates intensities using Otsu, local adaptive thresholding, or a fixed cutoff.',
 'Morphology':'Opening removes small bright regions; closing fills small dark gaps. Kernel size controls the scale.',
 'Contours':'Connected boundaries from the cleaned binary mask. Small contours are filtered; these are shapes, not classified objects.',
 'Lines':'Probabilistic Hough transform finds line segments in the Canny edge map. Segments are not automatically lanes.',
 'Road candidates':'White stripe shapes and near-horizontal lines are experimental marking candidates. Shadows, reflections and perspective can produce false candidates.',
 'Stripe mask':'Geometric white-stripe candidates. This mask does not establish a zebra crossing or stop line.',
 'Sobel magnitude':'Combines horizontal and vertical intensity derivatives. The display is normalized per frame, so brightness is not comparable across frames.',
 'Laplacian':'Absolute second spatial derivative, clipped to 8-bit display. Responds strongly to fine edges and noise.',
 'Morphological gradient':'Dilation minus erosion reveals local boundaries at the chosen morphology kernel size.',
 'Top hat':'Original grayscale minus its opening highlights bright details smaller than the chosen kernel.',
 'Black hat':'Closing minus original grayscale highlights dark details smaller than the chosen kernel.'
};
function paint(){
 const p=state.preview;if(!p)return;$('empty-state').hidden=true;$('frame').hidden=false;$('compare-control').hidden=state.view!=='compare';
 try{localStorage.setItem('traffic-lab-workspace',JSON.stringify({media:state.media.id,settings:state.settings,mode:state.mode,timestamp:Number($('timestamp').value)||0}));}catch{}
 $('frame').style.setProperty('--image-ratio',p.size[0]/p.size[1]);
 const selector=$('view-choice');let choices=state.view==='features'?p.features:state.view==='stages'?Object.fromEntries(p.ivp_steps.map((step,i)=>[String(i+1).padStart(2,'0')+' · '+step.title,step.url])):null;const selected=selector.value;
 selector.hidden=!choices;if(choices){selector.innerHTML=Object.keys(choices).map(k=>`<option>${escapeHTML(k)}</option>`).join('');if(selected in choices)selector.value=selected;else if(state.view==='stages')selector.selectedIndex=Math.min(state.step,p.ivp_steps.length-1);}
 $('base-image').src=choices?choices[selector.value]:p.processed;$('base-image').alt=choices?selector.value:'Processed traffic frame';$('before-image').src=p.original;
 for(const id of ['before-image','wipe-line','original-label','processed-label'])$(id).hidden=state.view!=='compare';
 $('concept-text').textContent=state.view==='features'?concepts[selector.value]||'Intermediate feature view.':state.view==='stages'?`Processing stage: ${selector.value}. Inspect changes between consecutive stages to understand each operation.`:'Compare at matching resolution. The original source stays intact; colour masks are extracted from the original colour frame.';
 $('time-label').textContent=p.timestamp.toFixed(3)+' s';quality(p.measurements.original,p.measurements.processed,'quality-stats');drawHistogram(p.histograms);qualityHints(p.measurements);
 if(!$('mask-list').children.length)$('mask-list').innerHTML=Object.keys(p.features).map(k=>`<label><input type="checkbox" value="${escapeHTML(k)}" ${['Edges','Colour mask','White marking mask'].includes(k)?'checked':''}>${escapeHTML(k)}</label>`).join('');
 paintStages();updateWipe();paintMotionLine();
}
function updateWipe(){const percent=$('wipe').value;$('before-image').style.clipPath=`inset(0 ${100-percent}% 0 0)`;$('wipe-line').style.left=percent+'%';}
const metrics=[['brightness','Brightness','0–255',1,1],['contrast','Contrast','Standard deviation',1,1],['laplacian_variance','Edge detail','Laplacian variance',1,1],['shadow_fraction','Deep shadows','Pixels ≤ 10',100,1],['highlight_fraction','Highlights','Pixels ≥ 245',100,1],['entropy_bits','Entropy','0–8 bits',1,2]];
function quality(before,after,target){$(target).innerHTML=metrics.map(([key,label,unit,scale,places])=>`<div class="stat"><div class="stat-label">${label}<small>${unit}</small></div><div class="stat-value">${((after[key]||0)*scale).toFixed(places)}${scale===100?'%':''}<small>was ${((before[key]||0)*scale).toFixed(places)}${scale===100?'%':''}</small></div></div>`).join('');}
function drawHistogram(hist){const max=Math.max(1,...hist.original,...hist.processed);$('histogram').innerHTML=['original','processed'].map((name,i)=>`<polyline fill="none" stroke="${i?'#216755':'#a8b4a2'}" stroke-width="1.5" points="${hist[name].map((v,x)=>`${x},${98-v/max*94}`).join(' ')}"/>`).join('');}
function qualityHints(measurements){const hints=[];const before=measurements.original,after=measurements.processed;if(before.brightness<55)hints.push('Dark input: try Low light or a small gamma increase. Inspect highlights after adjustment.');if(after.highlight_fraction>before.highlight_fraction+.03)hints.push('More highlights are clipped. Consider lowering exposure, gamma, or contrast clipping.');if(after.laplacian_variance<70)hints.push('Low edge detail may indicate blur, or simply a smooth scene. Sharpening cannot recover missing detail.');if(after.contrast<28)hints.push('Low contrast: compare CLAHE with a small percentile stretch. Watch for amplified noise.');if(!hints.length)hints.push('No strong heuristic quality flags. Check the image visually before exporting.');$('quality-hints').innerHTML=hints.map(h=>`<p>${h}</p>`).join('');}
function inspectTab(name){for(const panel of ['quality','region','ai'])$(panel+'-panel').hidden=name!==panel;document.querySelectorAll('[data-inspect]').forEach(b=>b.classList.toggle('active',b.dataset.inspect===name));}
let dragStart=null, dragWipe=false;
function regionPoint(event){const rect=$('frame').getBoundingClientRect();return [Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width)),Math.max(0,Math.min(1,(event.clientY-rect.top)/rect.height))];}
function drawRegion(){if(!state.region)return;const [x1,y1,x2,y2]=state.region;Object.assign($('region-box').style,{left:x1*100+'%',top:y1*100+'%',width:(x2-x1)*100+'%',height:(y2-y1)*100+'%'});$('region-box').hidden=false;}
async function measureRegion(){clearSurvey();const revision=state.revision;try{const result=await api('/api/region',{...payload(),rectangle:state.region});if(revision!==state.revision)return;quality(result.original,result.processed,'region-stats');const text=document.createElement('p');text.className='hint';text.textContent=`Processed pixel bounds: ${result.bounds_processed_xyxy_exclusive.join(', ')}. Source corner centres: ${result.source_corner_pixel_centres.map(p=>p.map(v=>v.toFixed(1)).join(', ')).join(' → ')}.`;$('region-stats').append(text);const button=document.createElement('button');button.className='quiet';button.textContent='Download region measurements';button.onclick=()=>downloadJSON({source:state.media.name,timestamp:state.preview.timestamp,settings:state.preview.settings,...result},'region-measurements.json');$('region-stats').append(button);}catch(e){notify(e.message,true);}}
function downloadJSON(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function links(items){return items.map(item=>`<a href="${escapeHTML(item.url)}">↓ ${escapeHTML(item.label)}</a>`).join('');}
function jobMessage(run){
 const s=run.status,parts=[s.message||''];
 const total=run.report?.info?.frame_count||run.report?.source_info?.frame_count;
 if(Number.isFinite(s.frames))parts.push(`${s.frames}${total?' / '+total:''} ${s.frames===1&&!total?'frame':'frames'} processed`);
 if(Number.isFinite(s.fps)&&s.frames>=30)parts.push(`${s.fps.toFixed(1)} processing frames/s`);
 return parts.filter(Boolean).join(' · ');
}
function showJob(run){showMotionResult(run);state.job=run.id;$('active-job').hidden=false;$('job-title').textContent=run.source+' · '+run.status.state;$('job-progress').value=run.status.progress||0;$('job-message').textContent=jobMessage(run);$('job-downloads').innerHTML=links(run.downloads);const active=['queued','running','encoding'].includes(run.status.state);try{if(active||run.status.state==='unknown')localStorage.setItem('traffic-lab-active-job',run.id);else if(localStorage.getItem('traffic-lab-active-job')===run.id)localStorage.removeItem('traffic-lab-active-job');}catch{}$('cancel-job').hidden=!active;$('cancel-job').disabled=false;clearTimeout(jobTimer);if(active||run.status.state==='unknown')jobTimer=setTimeout(pollJob,1500);}
function showFrameExport(run){const card=$('frame-export-result');card.hidden=false;card.innerHTML=`<strong>Saved frame · ${escapeHTML(run.source)}</strong><p>${escapeHTML(run.status.message||'Frame export ready.')}</p><div class="downloads">${links(run.downloads)}</div>`;}
async function pollJob(){try{showJob(await api('/api/run?id='+encodeURIComponent(state.job)));}catch(e){$('job-message').textContent=e.message;jobTimer=setTimeout(pollJob,5000);}}
async function startJob(ai){try{const run=await api('/api/job',{...payload(),masks:masks(),ai});showJob(run);notify('Processing started. You can continue inspecting the frame.');}catch(e){notify(e.message,true);}}
async function loadRuns(){try{state.runs=await api('/api/runs');paintRuns();}catch(e){notify(e.message,true);}}
function paintRuns(){const text=$('run-search').value.toLowerCase(),filter=$('run-filter').value;const runs=state.runs.filter(r=>(r.source+' '+r.id).toLowerCase().includes(text)&&(!filter||r.status.state===filter));$('runs').innerHTML=runs.map(run=>`<article class="run-row"><div><h3>${escapeHTML(run.source)}</h3><p>${escapeHTML(run.id)} · ${escapeHTML(run.status.message||'')}</p></div><span class="status-chip">${escapeHTML(run.status.state)}</span><button class="quiet" data-run="${escapeHTML(run.id)}">Open result ↗</button></article>`).join('')||'<p class="hint">No runs match. Export a frame or process a video to start your library.</p>';$('runs').querySelectorAll('[data-run]').forEach(button=>button.onclick=()=>openRun(button.dataset.run));}
async function openRun(id){try{const run=await api('/api/run?id='+encodeURIComponent(id));$('result-title').textContent=run.source;const report=run.report,ai=report.ai;let html=`<p>${escapeHTML(run.status.message||'')}</p>`;if(run.preview)html+=run.preview.video?`<video controls src="${escapeHTML(run.preview.url)}"></video>`:`<img src="${escapeHTML(run.preview.url)}" alt="${run.preview.name==='detections.png'?'Object detections, not violation decisions':'Processed export'}">`;if(run.preview?.name==='detections.png')html+='<p>Cyan boxes show object detections, not violations. Download the processed image to inspect reported events.</p>';
 if(ai){const total=Object.values(ai.events_by_rule||{}).reduce((a,b)=>a+b,0);html+=`<h3>${total} reported events</h3><p>Zero events does not prove the scene is violation-free. “Cannot assess” means evidence or scene context was insufficient.</p><table><thead><tr><th>Rule / assessment</th><th>Frame assessments</th></tr></thead><tbody>${Object.entries(ai.assessment_counts||{}).map(([k,v])=>`<tr><td>${escapeHTML(k.replaceAll('_',' '))}</td><td>${v}</td></tr>`).join('')}</tbody></table>`;}
 html+=`<div class="downloads">${links(run.downloads)}</div>`;if(report.motion&&run.status.state==='complete')html+=motionSummary(report.motion);if(report.kind==='ivp_marking_survey')html+=surveySummary(report);if(report.settings)html+='<button id="reuse-settings" class="quiet">Use these adjustments</button>';html+=`<details><summary>Full processing record</summary><pre>${escapeHTML(JSON.stringify(report,null,2))}</pre></details>`;$('result-body').innerHTML=html;if($('reuse-settings'))$('reuse-settings').onclick=()=>{changeSettings({...state.config.defaults,...report.settings},'Saved run');$('result-dialog').close();$('library').hidden=true;$('workspace').hidden=false;notify('Saved adjustments applied.');};if(report.motion&&run.status.state==='complete')showMotionResult(run);$('result-dialog').showModal();if(['queued','running','encoding','unknown'].includes(run.status.state))showJob(run);
 }catch(e){notify(e.message,true);}}

async function startReview(){if(!state.media)return;try{const source=state.media.id;const stamp=Number($('timestamp').value)||0;const result=await api('/api/review',payload());state.review={id:result.id,source,stamp};$('review-output').textContent='Reviewing locally… You can keep using the workspace.';actions();reviewTimer=setTimeout(pollReview,1500);}catch(e){notify(e.message,true);}}
async function pollReview(){if(!state.review)return;try{const result=await api('/api/review?id='+state.review.id);if(result.state==='running'){reviewTimer=setTimeout(pollReview,1500);return;}if(result.state==='failed')throw Error(result.error);const review=result.review;if(state.media?.id===state.review.source){$('review-output').textContent=review.observation.summary;const note=document.createElement('p');note.textContent=`Original frame at ${review.timestamp??state.review.stamp}s · ${review.duration_seconds.toFixed(1)}s · Unverified model description.`;$('review-output').append(note);const button=document.createElement('button');button.className='quiet';button.textContent='Download review';button.onclick=()=>downloadJSON(review,'scene-review.json');$('review-output').append(button);}else notify('Review finished for the previous source. Reopen that source and request a new review if needed.');state.review=null;actions();}catch(e){state.review=null;$('review-output').textContent=e.message;notify(e.message,true);actions();}}

async function init(){try{state.config=await api('/api/config');if(state.config.vehicle_tracking_ready===false)$('motion-mode').value='ivp';motionModeChanged();if(!state.config.samples.some(s=>s.name==='india-city.mp4')){$('motion-demo').disabled=true;$('motion-demo').textContent='Indian demo unavailable on this computer';}state.settings=copy(state.config.defaults);$('connection').textContent='Connected';$('preset').innerHTML='<option value="" disabled>Custom adjustments</option>'+Object.keys(state.config.presets).map(k=>`<option>${escapeHTML(k)}</option>`).join('');$('sample').insertAdjacentHTML('beforeend',state.config.samples.map(s=>`<option value="${escapeHTML(s.name)}">${escapeHTML(s.label)}</option>`).join(''));makeControls();setMode('automatic',false);}catch(e){$('connection').textContent='Offline';notify(e.message,true);return;}
 $('target-mark').onclick=()=>{if(!state.preview)return;$('timestamp').value=0;schedule();calibrating=false;selectingTarget=true;targetRectangle=null;targetStart=null;state.regionTool=false;$('viewport').scrollIntoView({behavior:'smooth',block:'center'});$('target-status').textContent='Drag a tight box around the vehicle in frame zero.';};$('target-clear').onclick=clearTarget;$('target-demo').onclick=()=>{if(state.media?.name!=='india-delhi-overhead.mp4'){notify('Load the Delhi intersection sample first.',true);return;}$('timestamp').value=0;schedule();targetRectangle=[.49,.60,.64,.69];selectingTarget=false;drawTarget();};
 $('speed-mark').onclick=()=>{if(state.media?.kind!=='video'||!state.preview||state.rendering||state.pending){notify('Wait for the video preview to finish.',true);return;}$('timestamp').value=0;$('time-label').textContent='0.00 s';state.step=0;document.querySelector('[data-view="stages"]').click();$('view-choice').selectedIndex=0;paint();schedule();selectingTarget=false;targetStart=null;calibrating=true;calibrationPoints=[];calibrationSource={media_id:state.media.id,source_revision:state.media.source_revision,reference_frame:0};$('speed-enabled').checked=false;state.regionTool=false;$('region-tool').setAttribute('aria-pressed','false');drawCalibration();$('viewport').scrollIntoView({behavior:'smooth',block:'center'});};$('speed-clear').onclick=clearCalibration;$('speed-enabled').onchange=drawCalibration;
 $('motion-demo').onclick=()=>sample('india-city.mp4');$('motion-run').onclick=startMotion;$('motion-mode').onchange=motionModeChanged;$('motion-axis').onchange=paintMotionLine;$('motion-position').oninput=paintMotionLine;
 document.querySelectorAll('.incident-setup input,.incident-setup select,.incident-setup textarea').forEach(el=>el.addEventListener('input',paintIncidents));
 $('incident-frame-zero').onclick=()=>{$('timestamp').value=0;state.step=0;schedule();$('frame').scrollIntoView({behavior:'smooth',block:'center'});};
 $('survey-run').onclick=runSurvey;$('survey-select').onclick=selectSurveyRegion;
 $('processing-mode').onchange=()=>setMode($('processing-mode').value);$('ivp-workspace').onclick=()=>setArea('ivp');$('ai-workspace').onclick=()=>setArea('ai');$('previous-stage').onclick=()=>selectStage(state.step-1);$('next-stage').onclick=()=>selectStage(state.step+1);
 $('open-footage').onclick=()=>$('upload').click();$('jump-controls').onclick=()=>document.querySelector('.tools').scrollIntoView({behavior:'smooth'});$('jump-inspector').onclick=()=>document.querySelector('.inspector').scrollIntoView({behavior:'smooth'});
 $('preset').onchange=()=>changeSettings(state.config.presets[$('preset').value],$('preset').value);$('reset').onclick=()=>{$('preset').value='Original';changeSettings(state.config.defaults,'Original');};$('undo').onclick=()=>{state.redo.push(copy(state.settings));state.settings=state.undo.pop();$('settings-label').textContent='Custom';sync();schedule();};$('redo').onclick=()=>{state.undo.push(copy(state.settings));state.settings=state.redo.pop();sync();schedule();};
 $('sample').onchange=()=>sample($('sample').value);$('try-sample').onclick=()=>{const name=state.config.samples.find(s=>s.name==='street.jpg')?.name||state.config.samples[0]?.name;$('sample').value=name;sample(name);};$('upload').onchange=()=>upload($('upload').files[0]);$('dropzone').ondragover=e=>{e.preventDefault();$('dropzone').classList.add('dragging');};$('dropzone').ondragleave=()=>$('dropzone').classList.remove('dragging');$('dropzone').ondrop=e=>{e.preventDefault();$('dropzone').classList.remove('dragging');upload(e.dataTransfer.files[0]);};
 document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{state.view=button.dataset.view;document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',b===button?'true':'false');});$('view-choice').innerHTML='';paint();});$('view-choice').onchange=()=>{state.step=$('view-choice').selectedIndex;paint();};$('wipe').oninput=updateWipe;$('timestamp').oninput=()=>{$('time-label').textContent=Number($('timestamp').value).toFixed(2)+' s';schedule();};
 document.querySelectorAll('[data-inspect]').forEach(button=>button.onclick=()=>inspectTab(button.dataset.inspect));$('region-tool').onclick=()=>{state.regionTool=!state.regionTool;$('frame').classList.toggle('selecting',state.regionTool);$('region-tool').setAttribute('aria-pressed',String(state.regionTool));if(state.regionTool)inspectTab('region');};$('frame').onpointerdown=e=>{if(state.rendering||state.pending||!state.preview)return;if(selectingTarget){targetStart=regionPoint(e);$('frame').setPointerCapture(e.pointerId);return;}if(calibrating){if(!$('base-image').complete||!$('base-image').naturalWidth)return;if(Number($('timestamp').value)!==0||state.preview.timestamp!==0){notify('Return to frame zero before marking road corners.',true);return;}calibrationPoints.push(regionPoint(e));if(calibrationPoints.length===4){calibrating=false;$('speed-enabled').checked=true;}drawCalibration();return;}if(state.regionTool)dragStart=regionPoint(e);else if(state.view==='compare'){dragWipe=true;$('wipe').value=regionPoint(e)[0]*100;updateWipe();}else return;$('frame').setPointerCapture(e.pointerId);};$('frame').onpointermove=e=>{if(targetStart){const end=regionPoint(e);targetRectangle=[Math.min(targetStart[0],end[0]),Math.min(targetStart[1],end[1]),Math.max(targetStart[0],end[0]),Math.max(targetStart[1],end[1])];drawTarget();return;}if(dragWipe){$('wipe').value=regionPoint(e)[0]*100;updateWipe();return;}if(!dragStart)return;const end=regionPoint(e);state.region=[Math.min(dragStart[0],end[0]),Math.min(dragStart[1],end[1]),Math.max(dragStart[0],end[0]),Math.max(dragStart[1],end[1])];drawRegion();};$('frame').onpointerup=()=>{if(targetStart){targetStart=null;selectingTarget=false;drawTarget();return;}dragWipe=false;if(dragStart&&state.region){dragStart=null;measureRegion();}dragStart=null;};$('frame').onpointercancel=()=>{targetStart=null;selectingTarget=false;dragStart=null;dragWipe=false;};$('clear-region').onclick=()=>{state.region=null;clearSurvey();$('region-box').hidden=true;$('region-stats').innerHTML='<p class="hint">No region selected.</p>';};
 $('export-frame').onclick=async()=>{try{$('export-frame').disabled=true;const run=await api('/api/export',{...payload(),masks:masks()});showFrameExport(run);notify('Frame and report saved. Downloads are ready below.');}catch(e){notify(e.message,true);}finally{actions();}};$('export-video').onclick=()=>startJob(false);$('analyse').onclick=()=>startJob(true);$('review').onclick=startReview;$('cancel-job').onclick=async()=>{try{await api('/api/cancel',{id:state.job});$('cancel-job').disabled=true;notify('Cancellation requested.');}catch(e){notify(e.message,true);}};
 $('save-settings').onclick=()=>downloadJSON(state.settings,'traffic-lab-settings.json');$('import-settings').onchange=async()=>{try{const file=$('import-settings').files[0];if(!file)return;if(file.size>65536)throw Error('Settings file is too large.');const value=JSON.parse(await file.text());const settings=value.settings||value;if(!settings||Array.isArray(settings)||typeof settings!=='object'||Object.keys(settings).some(k=>!(k in state.config.defaults)))throw Error('This is not a supported processing settings file.');await api('/api/validate-settings',{settings});changeSettings({...state.config.defaults,...settings},'Imported');notify('Settings loaded.');}catch(e){notify(e.message,true);}finally{$('import-settings').value='';}};
 $('history-button').onclick=()=>{$('workspace').hidden=true;$('library').hidden=false;loadRuns();};$('back-workspace').onclick=()=>{$('library').hidden=true;$('workspace').hidden=false;};$('refresh-runs').onclick=loadRuns;$('run-search').oninput=paintRuns;$('run-filter').onchange=paintRuns;$('close-result').onclick=()=>$('result-dialog').close();
 try{const saved=JSON.parse(localStorage.getItem('traffic-lab-workspace')||'null');if(saved){state.settings=await api('/api/validate-settings',{settings:saved.settings});setMode(saved.mode==='manual'?'manual':'automatic',false);sync();$('settings-label').textContent='Restored';await openMedia(await api('/api/media?id='+encodeURIComponent(saved.media)),saved.timestamp||0);}}catch{notify('Open footage to continue. Previously exported runs are still in Saved runs.');}
 try{const id=localStorage.getItem('traffic-lab-last-motion');if(id)showMotionResult(await api('/api/run?id='+encodeURIComponent(id)));}catch{}
 try{const id=localStorage.getItem('traffic-lab-active-job');if(id)showJob(await api('/api/run?id='+encodeURIComponent(id)));}catch{notify('Could not restore job progress. Check Saved runs or reload to retry.',true);}
}

function setMode(mode, rerender=true){
 state.mode=mode;$('processing-mode').value=mode;$('manual-settings').hidden=mode!=='manual';$('automatic-reasons').hidden=mode!=='automatic';
 if(rerender)schedule();
}
function setArea(area){
 $('workspace').hidden=false;$('library').hidden=true;
 state.area=area;document.body.classList.toggle('ai-workspace',area==='ai');
 $('ivp-workspace').className=area==='ivp'?'primary':'quiet';$('ai-workspace').className=area==='ai'?'primary':'quiet';
 $('workspace-label').textContent=area==='ivp'?'IVP WORKSPACE · AI ASSIST OPTIONAL':'AI WORKSPACE · EXPERIMENTAL';
 document.querySelector('.inspector-tabs').hidden=area==='ai';inspectTab(area==='ai'?'ai':'quality');
 state.view=area==='ivp'?'stages':'processed';document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===state.view);b.setAttribute('aria-pressed',String(b.dataset.view===state.view));});
 $('view-choice').innerHTML='';paint();
}
function selectStage(index){
 if(!state.preview)return;state.step=Math.max(0,Math.min(state.preview.ivp_steps.length-1,index));state.view='stages';
 document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view==='stages');b.setAttribute('aria-pressed',String(b.dataset.view==='stages'));});
 $('view-choice').innerHTML='';paint();$('stage-navigation').scrollIntoView({behavior:'smooth',block:'nearest'});
}
function paintStages(){
 const p=state.preview;if(!p)return;const steps=p.ivp_steps;
 $('ivp-board').hidden=state.area!=='ivp';$('stage-navigation').hidden=state.view!=='stages';
 $('automatic-reasons').innerHTML='<strong>Automatic plan</strong><ul>'+(p.automatic.reasons||[]).map(v=>'<li>'+escapeHTML(v)+'</li>').join('')+'</ul><p>'+escapeHTML(p.automatic.scope||'')+'</p><p>Automatic choices are conservative heuristics, not guaranteed optimal settings.</p>';
 if(state.view==='stages'){
 state.step=$('view-choice').selectedIndex;const step=steps[state.step];
 $('stage-title').textContent=`${state.step+1} / ${steps.length} · ${step.title}`;
 $('previous-stage').disabled=state.step===0;$('next-stage').disabled=state.step===steps.length-1;
 $('download-stage').href=step.download;
 const parent=steps.find(s=>s.id===step.parent);
 $('concept-text').textContent=`${step.branch} · Input: ${parent?parent.title:'uploaded frame'}. ${step.explanation} ${Object.keys(step.parameters).length?'Parameters: '+JSON.stringify(step.parameters):''}`;
 }
 $('stage-cards').innerHTML=steps.map((step,i)=>`<button class="stage-card ${state.view==='stages'&&state.step===i?'selected':''}" data-step="${i}" aria-label="Inspect stage ${i+1}: ${escapeHTML(step.title)}"><img loading="lazy" src="${escapeHTML(step.url)}" alt="${escapeHTML(step.title)}"><span class="step-number">${String(i+1).padStart(2,'0')} / ${escapeHTML(step.branch)}</span><strong>${escapeHTML(step.title)}</strong><small>Input: ${escapeHTML(steps.find(s=>s.id===step.parent)?.title||'uploaded frame')}</small></button>`).join('');
 $('stage-cards').querySelectorAll('[data-step]').forEach(button=>button.onclick=()=>selectStage(Number(button.dataset.step)));
}

let surveying=false, surveyRevision=0;
function surveyActions(){
 $('survey-select').disabled=!state.preview||state.rendering||state.pending||surveying;
 $('survey-run').disabled=!state.preview||!state.region||state.rendering||state.pending||surveying;
}
function clearSurvey(){
 surveyRevision++;$('survey-result').hidden=true;
 $('survey-status').textContent=state.region?'Selection changed. Run a fresh survey to save measurements.':'Select road only, excluding vehicles and buildings where possible. For video, this surveys the selected frame.';
 surveyActions();
}
function selectSurveyRegion(){
 state.view='stages';state.step=0;$('view-choice').innerHTML='';selectStage(0);
 state.regionTool=true;$('frame').classList.add('selecting');$('region-tool').setAttribute('aria-pressed','true');inspectTab('region');
 $('survey-status').textContent='Drag a rectangle over the road in the original-colour image below.';
 $('frame').scrollIntoView({behavior:'smooth',block:'center'});
}
function surveySummary(report){
 const s=report.summary;
 const rows=report.fragments.slice(0,100);
 return `<h2>Road-marking survey</h2><p>Original colour · frame ${report.timestamp_seconds.toFixed(3)} s · ${report.analysis_size.join(' × ')} analysis pixels</p>
 <div class="survey-metrics"><div><strong>${s.coverage_percent.toFixed(2)}%</strong><span>Candidate coverage in selection</span></div><div><strong>${s.fragments}</strong><span>Connected fragments</span></div><div><strong>${s.threshold_high_coverage_percent.toFixed(2)}–${s.threshold_low_coverage_percent.toFixed(2)}%</strong><span>Coverage across ±20 threshold test</span></div></div>
 <p>Mask agreement across thresholds: ${s.threshold_mask_iou===null?'not available (both empty)':(100*s.threshold_mask_iou).toFixed(1)+'% IoU'}. This measures threshold stability, not detection accuracy.</p>
 <details open><summary>Interpretation and limits</summary><ul>${report.limitations.map(t=>'<li>'+escapeHTML(t)+'</li>').join('')}</ul></details>
 <details><summary>How IVP produced these measurements</summary><p>Original RGB → selected road region → HSV white/yellow segmentation → opening removes specks → closing fills small gaps → connected components → area, bounding geometry and principal-axis orientation. Repeat at lower and higher brightness thresholds to expose sensitivity.</p><pre>${escapeHTML(JSON.stringify(report.parameters,null,2))}</pre></details>
 <details><summary>Fragment measurements (${s.fragments}; showing up to 100)</summary><div class="survey-table"><table><thead><tr><th>ID</th><th>Area px</th><th>Long side px</th><th>Short side px</th><th>Angle °</th><th>Clipped by ROI</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.id}</td><td>${r.area_px}</td><td>${r.long_side_px.toFixed(1)}</td><td>${r.short_side_px.toFixed(1)}</td><td>${r.orientation_deg_clockwise_from_right===null?'ambiguous':r.orientation_deg_clockwise_from_right.toFixed(1)}</td><td>${r.touches_roi_boundary?'yes':'no'}</td></tr>`).join('')}</tbody></table></div><p>Distances use pixel-centre geometry at analysis resolution; angle is clockwise from image right. CSV contains every fragment and source-image centres. No metre calibration is applied.</p></details>`;
}
async function runSurvey(){
 if(!state.region||surveying)return;
 const revision=surveyRevision;const request={...payload(),rectangle:[...state.region]};surveying=true;surveyActions();
 $('survey-status').textContent='Measuring original pixels and saving evidence…';
 try{
  const run=await api('/api/survey',request);
  if(revision!==surveyRevision){notify('Survey saved for the earlier selection. Find it in Saved runs.');return;}
  $('survey-result').innerHTML=surveySummary(run.report)+`<img class="survey-overlay" src="${escapeHTML(run.preview.url)}" alt="Selected road with candidate pixels in cyan and numbered fragments"><div class="downloads">${links(run.downloads)}</div>`;
  $('survey-result').hidden=false;$('survey-status').textContent='Survey saved. Cyan pixels are candidates; numbered boxes match the CSV. Review the mask before interpreting coverage.';
  $('survey-result').scrollIntoView({behavior:'smooth',block:'start'});
 }catch(e){$('survey-status').textContent=e.message;notify(e.message,true);}
 finally{surveying=false;surveyActions();}
}

let lastMotionRun=null, startingMotion=false;
function motionModeChanged(){
 document.querySelector('.target-setup').hidden=$('motion-mode').value==='vehicles';
 $('motion-mode-note').textContent=$('motion-mode').value==='vehicles'?'Whole-vehicle boxes from local YOLO11s; ByteTrack with bottom-centre continuity, IVP camera correction and speed. No LLM. Auto-rickshaw types are not classified. New tracks require at least four observations and 0.3 seconds before appearing.':'No AI model runs. Background subtraction discovers foreground regions; corner tracking follows their texture. A track may cover part of a vehicle, several touching vehicles, or another moving object. Use this mode to study motion and foreground activity; whole-vehicle tracking is the separate detector + IVP mode.';
 if($('motion-mode').value==='vehicles')clearTarget();
}
function motionActions(){
 const video=state.media?.kind==='video';$('motion-options').hidden=!video;
 $('speed-mark').disabled=!video||!state.preview||state.rendering||state.pending;
 $('motion-run').disabled=!video||!state.preview||state.rendering||state.pending||startingMotion;
 $('motion-note').textContent=video?'No per-vehicle selection needed. Fixed, elevated cameras work best. Speed appears automatically in px/s; measured road calibration enables km/h for all tracks.':'Open a video or load the demo. Still images cannot show movement.';
}
function paintMotionLine(){
 const line=$('motion-count-line'),axis=$('motion-axis').value,pos=Number($('motion-position').value);
 $('motion-line-value').textContent=pos+'%';line.hidden=state.area!=='ivp'||state.media?.kind!=='video';
 line.style.cssText=axis==='horizontal'?`left:0;top:${pos}%;width:100%;height:2px`:`left:${pos}%;top:0;height:100%;width:2px`;
 paintIncidents();
}
async function startMotion(){
 try{
  if($('motion-use-roi').checked&&!state.region)throw Error('Select a road region first, or uncheck the region option.');
  startingMotion=true;motionActions();
  const run=await api('/api/motion',{media:state.media.id,axis:$('motion-axis').value,position:Number($('motion-position').value)/100,rectangle:$('motion-use-roi').checked?state.region:null,calibration:speedCalibration(),target_rectangle:$('motion-mode').value==='ivp'?targetRectangle:null,tracking_mode:$('motion-mode').value,output_view:$('motion-view').value,incidents:incidentConfig()});
  showJob(run);$('active-job').scrollIntoView({behavior:'smooth',block:'center'});notify('Automatic tracking started. The video and speed measurements will appear when ready.');
 }catch(e){notify(e.message,true);}finally{startingMotion=false;motionActions();}
}
let selectingTarget=false, targetRectangle=null, targetStart=null;
function clearTarget(){selectingTarget=false;targetRectangle=null;targetStart=null;drawTarget();}
function drawTarget(){const box=$('target-box');box.hidden=!targetRectangle;if(targetRectangle){const [x,y,x2,y2]=targetRectangle;box.style.cssText=`left:${x*100}%;top:${y*100}%;width:${(x2-x)*100}%;height:${(y2-y)*100}%`;$('target-status').textContent='Selected target ready. Track positions and speed will be exported under ID SELECTED.';}else $('target-status').textContent='No selected target.';}
let calibrationPoints=[], calibrating=false, calibrationSource=null;
function clearCalibration(){calibrationPoints=[];calibrating=false;calibrationSource=null;$('speed-enabled').checked=false;$('speed-width').value='';$('speed-length').value='';drawCalibration();}
function drawCalibration(){
 const points=calibrationPoints.map(p=>p.map(v=>v*100).join(',')).join(' ');
 $('speed-overlay').innerHTML=(calibrationPoints.length>1?`<polygon points="${points}" fill="#c88cff22" stroke="#c88cff" stroke-width=".4"/>`:'')+calibrationPoints.map((p,i)=>`<circle cx="${p[0]*100}" cy="${p[1]*100}" r=".8" fill="#c88cff"/><text x="${p[0]*100+1}" y="${p[1]*100-1}" font-size="3" fill="#fff">${i+1}</text>`).join('');
 $('frame').classList.toggle('calibrating',calibrating);
 $('speed-status').textContent=calibrating?`Click corner ${calibrationPoints.length+1} of 4: ${['far-left','far-right','near-right','near-left'][calibrationPoints.length]}.`:calibrationPoints.length===4?($('speed-enabled').checked?'Four corners selected. Enter measured dimensions before analysing.':'Calibration disabled. Region estimates use px/s.'):'No calibration. Region estimates use px/s.';
}
function speedCalibration(){
 if(!$('speed-enabled').checked)return null;
 if(calibrationSource?.media_id!==state.media?.id||calibrationSource?.source_revision!==state.media?.source_revision)throw Error('Mark the road corners on this video before enabling km/h.');
 if(calibrationPoints.length!==4)throw Error('Mark all four road corners before enabling km/h.');
 const width=Number($('speed-width').value),length=Number($('speed-length').value);
 if(!(width>=.1&&width<=1000&&length>=.1&&length<=1000))throw Error('Enter measured road width and length (0.1–1000 metres).');
 return {...calibrationSource,points:calibrationPoints,width_m:width,length_m:length};
}
function clearIncidents(){
 for(const id of ['incident-enabled','incident-calibration-confirmed','incident-real-time','incident-synthetic'])$(id).checked=false;
 $('incident-condition').value='observe';$('incident-intervals').value='';$('incident-restricted').checked=false;
 paintIncidents();
}
function incidentConfig(){
 if(!$('incident-enabled').checked)return null;
 const rectangle=id=>{const v=$(id).value.split(',').map(x=>Number(x.trim())/100);if(v.length!==4||v.some(n=>!Number.isFinite(n)||n<0||n>1)||v[2]-v[0]<.02||v[3]-v[1]<.02)throw Error('Enter a rectangle as left, top, right, bottom percentages, at least 2% wide/high.');return v;};
 const start=Number($('incident-start').value)/100,end=Number($('incident-end').value)/100,pos=Number($('motion-position').value)/100;
 if($('incident-line').checked&&(!Number.isFinite(start)||!Number.isFinite(end)||start<0||end>1||end-start<.02))throw Error('Incident line end must be at least 2% beyond its start, within 0–100%.');
 const intervals=$('incident-intervals').value.trim().split('\n').filter(x=>x.trim()).map(row=>{const parts=row.split(',').map(s=>s.trim());if(parts.length!==3||parts[0]===''||parts[1]==='')throw Error('Condition timeline needs start, end, state on each line.');return {start:Number(parts[0]),end:Number(parts[1]),state:parts[2]};});
 return {enabled:true,line:$('incident-line').checked?($('motion-axis').value==='horizontal'?[[start,pos],[end,pos]]:[[pos,start],[pos,end]]):null,
  direction:$('incident-direction').value,condition:$('incident-condition').value,condition_intervals:intervals,
  zone:$('incident-zone').checked?rectangle('incident-zone-rect'):null,zone_role:$('incident-restricted').checked?'restricted':'observe',
  approach_zone:rectangle('incident-approach'),speed_limit_kmh:$('incident-limit').value===''?null:Number($('incident-limit').value),
  calibration_confirmed:$('incident-calibration-confirmed').checked,real_time_confirmed:$('incident-real-time').checked,synthetic:$('incident-synthetic').checked};
}
function paintIncidents(){
 const container=$('frame');if(!container)return;
 let overlay=$('incident-overlay');if(!overlay){overlay=document.createElementNS('http://www.w3.org/2000/svg','svg');overlay.id='incident-overlay';overlay.setAttribute('viewBox','0 0 100 100');overlay.setAttribute('preserveAspectRatio','none');overlay.setAttribute('aria-label','Configured incident geometry');container.appendChild(overlay);}
 overlay.innerHTML='';overlay.style.display=(!$('incident-enabled').checked||state.area!=='ivp')?'none':'block';
 if(!$('incident-enabled').checked){$('incident-status').textContent='Off. Existing tracking and speed analysis are unchanged.';return;}
 try{const c=incidentConfig();let shapes='';if(c.line)shapes+=`<line x1="${c.line[0][0]*100}" y1="${c.line[0][1]*100}" x2="${c.line[1][0]*100}" y2="${c.line[1][1]*100}" stroke="#fa783c" stroke-width=".6"/>`;
 for(const [rect,color] of [[c.zone,'#a078fa'],[c.condition==='stop_required'?c.approach_zone:null,'#50d2d2']])if(rect)shapes+=`<rect x="${rect[0]*100}" y="${rect[1]*100}" width="${(rect[2]-rect[0])*100}" height="${(rect[3]-rect[1])*100}" fill="none" stroke="${color}" stroke-width=".4"/>`;
 overlay.innerHTML=shapes;$('incident-status').textContent=`${c.synthetic?'Synthetic test. ':''}Review enabled. Geometry belongs to the first frame. ${Number($('timestamp').value)!==0?'Return to frame zero to verify placement. ':''}Speeding and missed-stop review withhold conclusions without confirmed calibration and real-time footage.`;
 }catch(e){$('incident-status').textContent=e.message;}
}
function incidentSummary(review){
 if(!review?.enabled)return '';
 const events=review.events||[],counts=review.counts||{};
 return `<section class="incident-review"><h3>${review.configuration.synthetic?'Synthetic incident review':'Incident review'}</h3><p><strong>${counts.candidate||0} review candidates</strong> · ${counts.observation||0} neutral observations · ${counts.withheld||0} withheld assessments.</p><p class="hint">Conditions were configured by the user. These are review candidates, not legal findings. Zero candidates does not establish compliant driving.</p>${review.invalid_reason?`<p class="error">${escapeHTML(review.invalid_reason)}</p>`:''}<details open><summary>Review evidence · first ${Math.min(events.length,20)} of ${review.event_count} assessments</summary><div class="incident-cards">${events.slice(0,20).map(e=>`<article class="incident-card">${e.thumbnail_url?`<img loading="lazy" src="${escapeHTML(e.thumbnail_url)}" alt="Evidence for ${escapeHTML(e.event_id)}">`:''}<strong>${escapeHTML(e.status)} · ${escapeHTML(e.type.replaceAll('_',' '))}</strong><p>${Number(e.timestamp_seconds).toFixed(2)} s · track ${escapeHTML(e.track_id)}${e.synthetic?' · SYNTHETIC':''}</p><p>${escapeHTML(e.reason)}</p>${e.measurements.speed!=null?`<p>${Number(e.measurements.speed).toFixed(2)} ${escapeHTML(e.measurements.speed_unit)}${e.measurements.threshold_kmh!=null?' · threshold '+Number(e.measurements.threshold_kmh)+' km/h':''}</p>`:''}</article>`).join('')}</div></details><p class="hint">${escapeHTML(review.thumbnail_policy)} Full timestamps, quality, coordinates, settings and all assessments are in the incident JSONL/CSV and evidence ZIP.</p></section>`;
}
function motionSummary(m){
 const names=m.line.axis==='horizontal'?['Down','Up']:['Right','Left'];
 const total=m.crossings.positive+m.crossings.negative;
 const bars=m.timeline.map((b,i)=>`<rect x="${i/m.timeline.length*600}" y="${b.activity_percent===null?0:100-b.activity_percent}" width="${Math.max(1,600/m.timeline.length)}" height="${b.activity_percent===null?100:b.activity_percent}" fill="${b.activity_percent===null?'#e6e7e2':'#267f76'}"><title>${b.start.toFixed(2)}–${b.end.toFixed(2)}s: ${b.activity_percent===null?'excluded':b.activity_percent.toFixed(2)+'% moving area'}</title></rect>`).join('');
 const speed=m.selected_target?.speed||m.speed;
 const synthetic=m.incidents?.configuration?.synthetic===true;
 const speedInfo=speed?`<div class="speed-report"><h3>${speed.calibrated?(synthetic?'Synthetic speed · declared virtual scale':'Calibrated region speed'):'Image motion speed'}</h3><strong>${speed.sample_mean===null?'No stable estimates':speed.sample_mean.toFixed(1)+' '+escapeHTML(speed.unit)}</strong><p>${m.selected_target?'Selected target':m.uses_ai?'Vehicle tracks':'Moving texture regions'}: mean of accepted track samples · ${speed.accepted_track_samples} samples. ${speed.calibrated?(synthetic?'Uses declared synthetic dimensions; this is not a measured real-world speed.':'Uses your measured road patch.'):'No physical calibration: these are pixels/second, not km/h.'} Estimates appear beside stable tracks and in the trajectories CSV.</p><p class="hint">${escapeHTML(speed.meaning)} ${speed.invalid_reason?escapeHTML(speed.invalid_reason):''}</p></div>`:'';
 return `<h2>${m.uses_ai?'Automatic vehicle tracking + IVP':'IVP foreground and texture tracking'}</h2>${m.tracking?`<p><strong>${m.tracking.confirmed_tracks} confirmed track IDs</strong> · longest ${m.tracking.longest_track_seconds.toFixed(1)} s · ${m.tracking.recovered_after_short_occlusion} short-gap recoveries. IDs are not a verified unique vehicle count.</p>`:''}${m.selected_target?`<p><strong>Selected target:</strong> ${escapeHTML(m.selected_target.status)} · ${m.selected_target.tracked_frames} frames tracked. ${escapeHTML(m.selected_target.limitation)}</p>`:''}${m.tracking?.recoveries_from_repeated_weak_observations?`<p class="hint">Across the full frame, ${m.tracking.recoveries_from_repeated_weak_observations} short gaps recovered through two consecutive observed detections. Competing matches are rejected; each recovery collects a fresh speed window.${m.tracking.recoveries_from_robust_geometry?` ${m.tracking.recoveries_from_robust_geometry} used robust recent-position geometry to recover from prediction drift.`:''}</p>`:''}${m.tracking?.ambiguous_overlap_frames?`<p class="hint">${m.tracking.ambiguous_overlap_frames} frames had overlapping vehicle hypotheses. IDs marked ? have speed and crossing measurements withheld.</p>`:''}${speed?.rejected_position_jumps?`<p class="hint">${speed.rejected_position_jumps} abrupt position changes reset the speed window. Track IDs remain unchanged; speed resumes after enough stable observations.</p>`:''}${!m.uses_ai?'<p class="hint">These are foreground texture regions. A vehicle can produce several tracks, and touching vehicles can share a region. This view measures image motion and occupied foreground area; its track and crossing totals are not vehicle counts.</p>':''}${speedInfo}<div class="survey-metrics"><div><strong>${total}</strong><span>${m.uses_ai?'Vehicle-candidate':'Moving-region'} line crossings · ${names[0]} ${m.crossings.positive} / ${names[1]} ${m.crossings.negative}</span></div><div><strong>${m.peak_activity_percent.toFixed(1)}%</strong><span>Peak foreground area in analysis region</span></div><div><strong>${m.measured_seconds.toFixed(2)} s</strong><span>Measured footage · ${m.suppressed_frames} frames excluded</span></div></div>
 <p class="hint">${m.ambiguous_frames||0} frames contained large or merged foreground regions. Existing tracks can continue when their evidence remains usable. Crossings can undercount or overcount where traffic overlaps.</p><h3>Movement over time</h3><svg class="activity-chart" viewBox="0 0 600 100" role="img" aria-label="Moving area percentage from 0 to 100 across the clip">${bars}</svg><p class="hint">Height = moving area (0–100%). Grey = no valid measurement. Left to right: 0–${m.timeline.at(-1)?.end.toFixed(2)} s. Hover for timestamps.</p>
 <details><summary>Camera correction and coordinate mapping</summary><p>${m.stabilization?escapeHTML(m.stabilization.method):'No camera correction in this earlier run.'} ${m.stabilization?escapeHTML(m.stabilization.coordinate_frame):''}</p></details><details><summary>How the IVP analysis works</summary><p>Gaussian smoothing → adaptive background model (MOG2) → shadow removal → opening and closing → connected components → automatic Shi-Tomasi corner discovery and forward/backward Lucas-Kanade tracking (IVP-only), or local vehicle proposals and ByteTrack (vehicle mode) → trajectory and line-crossing logic. Forward/backward checked optical flow shows local movement as green arrows, including in merged traffic. It also guards against coherent camera movement. Speed needs at least eight observed positions and 0.5 seconds. Its window extends up to ${Number(speed?.maximum_window_seconds||1.2).toFixed(1)} seconds for this run; uncertain trajectories and abrupt position changes are withheld. A homography maps a measured road patch to metres. Heatmap values accumulate foreground duration per pixel.</p></details>
 <details><summary>What the result can and cannot tell you</summary><ul>${m.limitations.map(t=>'<li>'+escapeHTML(t)+'</li>').join('')}</ul></details>${incidentSummary(m.incidents)}`;
}
function showMotionResult(run){
 if(run.status.state!=='complete'||!run.report.motion||lastMotionRun===run.id)return;
 lastMotionRun=run.id;try{localStorage.setItem('traffic-lab-last-motion',run.id);}catch{}const poster=run.downloads.find(d=>d.name===(run.report.motion.output_view==='tracks'?'motion-tracks.png':'motion-mosaic.png'));const heat=run.downloads.find(d=>d.name==='motion-heatmap.png');
 $('motion-result').innerHTML=`<div class="eyebrow">COMPLETED ${run.report.motion.uses_ai?'VEHICLE + IVP':'IVP'} RUN · ${escapeHTML(run.source)}</div>`+`<button id="motion-play" class="quiet">Play result</button><video controls playsinline preload="metadata" poster="${poster?escapeHTML(poster.url.replace('/download/','/view/')):''}" src="${escapeHTML(run.preview.url)}"></video>`+motionSummary(run.report.motion)+`<p class="hint">Automatic IDs and speed estimates are drawn on the stabilized footage. Amber marks the counting line. The stage images below show the background model, shadow removal, cleaned foreground, optical flow and heatmap. Speed is withheld when a track is uncertain.</p>`+(heat?`<details><summary>Final movement heatmap</summary><img src="${escapeHTML(heat.url.replace('/download/','/view/'))}" alt="Accumulated motion heatmap"></details>`:'')+`<div class="downloads">${links(run.downloads)}</div>`;
 const movie=$('motion-result').querySelector('video'),play=$('motion-play');
 play.onclick=()=>{if(movie.paused)movie.play().catch(e=>notify('Playback failed: '+e.message,true));else movie.pause();};movie.onplay=()=>play.textContent='Pause result';movie.onpause=()=>play.textContent='Play result';
 const stages=run.downloads.filter(d=>['motion-background.png','motion-raw-foreground.png','motion-shadows.png','motion-mask.png','motion-flow.png','motion-tracks.png'].includes(d.name));if(stages.length)$('motion-result').insertAdjacentHTML('beforeend','<details><summary>Inspect the motion-processing stages at peak activity</summary><div class="motion-stage-grid">'+stages.map(d=>`<figure><img src="${escapeHTML(d.url.replace('/download/','/view/'))}" alt="${escapeHTML(d.label)}"><figcaption>${escapeHTML(d.label)}</figcaption></figure>`).join('')+'</div></details>');
 $('motion-result').hidden=false;$('motion-result').scrollIntoView({behavior:'smooth',block:'start'});
}

init();
