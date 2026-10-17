const $ = id => document.getElementById(id);
const headers = () => ({'X-API-Key': $('key').value});
async function request(url, options={}) {
  const response = await fetch(url, {...options, headers: {...headers(), ...options.headers}});
  if (!response.ok) { const body = await response.json().catch(()=>({})); throw Error(body.detail || `Request failed (${response.status})`); }
  return response.json();
}
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
$('analysisTab').onclick = () => {$('analysis').classList.remove('hidden'); $('review').classList.add('hidden');};
$('reviewTab').onclick = () => {$('analysis').classList.add('hidden'); $('review').classList.remove('hidden');};
fetch('/health').then(r=>r.json()).then(h=>{if(h.review_enabled)$('reviewTab').classList.remove('hidden'); if(!h.model_ready)$('progress').textContent='No trained model installed. Run the local training step first.';});
$('upload').onclick = async () => {
  if (!$('key').value || !$('file').files.length) { $('progress').textContent='Enter your API key and select a MOV video.'; return; }
  $('upload').disabled=true; $('events').replaceChildren(); $('events').classList.add('empty'); $('events').textContent='Analyzing your recording…';
  try {
    const form = new FormData(); form.append('file', $('file').files[0]);
    $('progress').textContent='Uploading recording…';
    const {job_id} = await request('/api/v1/analyze', {method:'POST',body:form});
    const began=Date.now();
    while (Date.now()-began<300000) {
      const job = await request(`/api/v1/jobs/${job_id}`);
      if(job.status==='failed')throw Error(job.error);
      if(job.status==='done') {render(job); $('progress').textContent='Analysis complete. Review the evidence before drawing a conclusion.'; return;}
      $('progress').textContent=`Processing locally · ${Math.round((Date.now()-began)/1000)}s`;
      await wait(1500);
    }
    throw Error('Analysis exceeded five minutes. Retry or check the service.');
  } catch(e) {$('progress').textContent=e.message; $('events').textContent='Analysis unavailable.';}
  finally {$('upload').disabled=false;}
};
function render(job) {
  $('events').replaceChildren(); $('events').classList.remove('empty');
  $('resultTitle').textContent=job.verdict==='violation'?'Possible signs of violations':'No violation detected';
  if(!job.violations.length){$('events').textContent='The experimental model did not flag an event. This does not establish that every procedure was followed.';return;}
  for(const event of job.violations) {
    const card=document.createElement('article'), title=document.createElement('h3'), text=document.createElement('p'), rule=document.createElement('p');
    title.textContent=`${event.timecode_sec.toFixed(1)}s · ${event.type}`;text.textContent=event.description;rule.textContent='Regulatory mapping: pending human verification';card.append(title,text);
    for(const frame of event.evidence_frames){const img=document.createElement('img');img.src=`data:image/jpeg;base64,${frame.image_base64}`;img.alt=`Evidence at ${frame.timestamp_sec} seconds`;card.append(img);}
    card.append(rule);$('events').append(card);
  }
}
let records=[], videoURL;
$('load').onclick=async()=>{try{records=await request('/api/local/dataset');$('videos').replaceChildren();for(const row of records){const option=document.createElement('option');option.value=row.id;option.textContent=`${row.id} · ${(row.raw_label||[]).join(' / ')}`;$('videos').append(option);}await showVideo();}catch(e){$('reviewStatus').textContent=e.message;}};
async function showVideo(){const row=records.find(r=>r.id===$('videos').value);if(!row)return;try{const r=await fetch(`/api/local/video/${row.id}`,{headers:headers()});if(!r.ok)throw Error('Cannot load recording');if(videoURL)URL.revokeObjectURL(videoURL);videoURL=URL.createObjectURL(await r.blob());$('player').src=videoURL;$('metadata').textContent=`${row.duration_sec.toFixed(1)}s · ${row.width} × ${row.height} · hash group ${row.sha256.slice(0,12)}`;const a=row.annotation||{};const stamp=Number.parseFloat((row.raw_label||[])[0])||0;$('start').value=a.start_sec??Math.max(0,stamp-2);$('end').value=a.end_sec??Math.min(row.duration_sec,stamp+2);$('type').value=a.type||'';$('observation').value=a.observation||'';$('rule').value=a.rule_url||'';$('clause').value=a.rule_clause||'';$('player').currentTime=stamp;$('reviewStatus').textContent='';}catch(e){$('reviewStatus').textContent=e.message;}}
$('videos').onchange=showVideo;
$('save').onclick=async()=>{try{const annotation={start_sec:Number($('start').value),end_sec:Number($('end').value),type:$('type').value,observation:$('observation').value,rule_url:$('rule').value,rule_clause:$('clause').value};await request(`/api/local/annotations/${$('videos').value}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(annotation)});records.find(r=>r.id===$('videos').value).annotation=annotation;$('reviewStatus').textContent='Annotation saved locally.';}catch(e){$('reviewStatus').textContent=e.message;}};
