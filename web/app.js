'use strict';
const $ = (id) => document.getElementById(id);
const names = {overview:'Visão geral',experiment:'Investigações / Publicada',investigations:'Investigações',evidence:'Evidências',audit:'Integridade e limites'};
let activeInvestigation = null;
const decimal = new Intl.NumberFormat('pt-BR',{maximumFractionDigits:1,minimumFractionDigits:1});
const dateOnlyFormatter = new Intl.DateTimeFormat('pt-BR');
const instantFormatter = new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short',timeZone:'UTC'});
async function api(path,opts={}){
  const response=await fetch(path,{cache:'no-store',headers:{'Content-Type':'application/json'},...opts});
  let data;try{data=await response.json();}catch{throw new Error(`Resposta inesperada (${response.status})`);}
  if(!response.ok)throw new Error(data.detail || data.error || `HTTP ${response.status}`);
  return data;
}
function element(tag,text,cls){const n=document.createElement(tag);if(text!==undefined&&text!==null)n.textContent=String(text);if(cls)n.className=cls;return n;}
function empty(container,message){container.replaceChildren(element('p',message));}
function toast(message){const n=$('toast');n.textContent=message;n.classList.add('visible');window.setTimeout(()=>n.classList.remove('visible'),3200);}
function formValues(form){const obj={};for(const [key,value] of new FormData(form))obj[key]=String(value).trim();return obj;}
function formatDate(value){if(!value)return'';const [year,month,day]=value.slice(0,10).split('-').map(Number);return dateOnlyFormatter.format(new Date(year,month-1,day));}
function formatInstant(value){return value?`${instantFormatter.format(new Date(value))} UTC`:'';}
function formatPeriod(start,end,withTime=false){const format=withTime?formatInstant:formatDate;if(start&&end)return`${format(start)} → ${format(end)}`;if(start)return`desde ${format(start)}`;if(end)return`até ${format(end)}`;return'Não informado';}
function observationText(item){if(item.observed_at)return`Observado em ${formatInstant(item.observed_at)}`;if(item.observed_start||item.observed_end)return`Janela observada: ${formatPeriod(item.observed_start,item.observed_end,true)}`;return'Observação não informada';}
async function postForm(form,path,messageEl,onSuccess,transform){
  const message=$(messageEl);message.textContent='Registrando...';message.className='form-message';
  const submit=form.querySelector('[type=submit]');submit.disabled=true;
  try{let body=formValues(form);if(transform)body=transform(body);
    const response=await api(path,{method:'POST',body:JSON.stringify(body)});
    message.textContent=response.created===false?'Registro idêntico já existia (idempotência).':'Registrado com sucesso.';
    message.classList.add('success');form.reset();await onSuccess(response);toast(message.textContent);
  }catch(error){message.textContent=error.message;message.classList.add('error');}
  finally{submit.disabled=false;}
}
function navigate(name){
  if(!names[name])return;
  const navName=name==='experiment'?'investigations':name;
  document.querySelectorAll('.view').forEach(n=>n.classList.toggle('hidden',n.id!==`view-${name}`));
  document.querySelectorAll('[data-view]').forEach(n=>{n.classList.toggle('active',n.dataset.view===navName);if(n.dataset.view===navName)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});
  $('crumb-name').textContent=names[name];$('sidebar').classList.remove('open');$('scrim').hidden=true;$('menu').setAttribute('aria-expanded','false');
  if(name==='investigations')refreshInvestigations();
  if(name==='experiment')refreshExperiment();
  if(name==='evidence')refreshEvidence();
  if(name==='audit')refreshAudit();
  $('main').focus({preventScroll:true});window.scrollTo({top:0,behavior:'auto'});
}
async function refreshExperiment(){
  try{const d=await api('/api/v1/investigations/published/exp-001');const map=d.metrics.mapbiomas;const met=d.metrics.inmet;const investigation=d.investigation;const [mapSource,inmetSource]=d.sources;
    $('experiment-title').textContent=investigation.title;
    $('experiment-question').textContent=d.question;
    $('published-period').textContent=formatPeriod(investigation.valid_start,investigation.valid_end);
    $('published-location').textContent=investigation.location_ref;
    $('published-protocol-date').textContent=`${formatDate(d.protocol.accepted_at)} · v${d.protocol.version}`;
    $('published-execution-date').textContent=`${formatDate(d.execution.executed_at)} · ${d.execution.id}`;
    $('experiment-status').textContent=d.compatibility.overall==='contextual_only'?'SOMENTE CONTEXTUAL':d.compatibility.overall;
    $('experiment-conclusion').textContent=d.conclusion;
    $('experiment-causal').textContent=d.compatibility.causal_claim?'SIM':'NÃO';
    $('metric-classes').textContent=map.class_count;
    $('metric-area').textContent=decimal.format(map.total_area_ha);
    $('metric-hours').textContent=`${met.valid_hours} / ${met.expected_hours}`;
    $('metric-rain').textContent=`${decimal.format(met.precipitation_total_mm)} mm`;
    $('temp-min').textContent=`${decimal.format(met.temperature_min_c)} °C`;
    $('temp-mean').textContent=`${decimal.format(met.temperature_mean_c)} °C`;
    $('temp-max').textContent=`${decimal.format(met.temperature_max_c)} °C`;
    $('inmet-quality').textContent=`${met.days} dias · ${met.missing_hours} horas ausentes · dados automáticos brutos e não validados`;
    $('mapbiomas-valid-period').textContent=formatPeriod(mapSource.valid_start,mapSource.valid_end);
    $('mapbiomas-provenance-dates').textContent=`Fonte publicada em ${formatDate(mapSource.source_published)} · obtida em ${formatDate(mapSource.obtained_at)}`;
    $('inmet-observed-period').textContent=formatPeriod(inmetSource.observed_start,inmetSource.observed_end,true);
    $('inmet-provenance-dates').textContent=`Período referido: ${formatPeriod(inmetSource.valid_start,inmetSource.valid_end)} · obtida em ${formatDate(inmetSource.obtained_at)}`;
    $('temporal-detail').textContent=d.compatibility.temporal.detail;
    $('spatial-detail').textContent=d.compatibility.spatial.detail;
    $('tests-result').textContent=`${d.reproducibility.tests_passed}/${d.reproducibility.tests_total}`;
    const repeated=Object.values(d.reproducibility.second_pass_created).reduce((total,value)=>total+value,0);
    $('second-pass-result').textContent=repeated;
    $('mapbiomas-source').textContent=`${mapSource.dataset} · ${mapSource.license} · SHA-256 ${mapSource.subset_sha256.slice(0,12)}…`;
    $('inmet-source').textContent=`${inmetSource.dataset} · SHA-256 ${inmetSource.subset_sha256.slice(0,12)}…`;
    const bars=$('land-cover-bars');bars.replaceChildren();
    map.top_classes.forEach(item=>{const row=element('div',null,'bar-row');const heading=element('div',null,'bar-heading');heading.append(element('strong',item.class),element('span',`${decimal.format(item.share_percent)}%`));const progress=element('progress');progress.max=100;progress.value=item.share_percent;progress.setAttribute('aria-label',`${item.class}: ${decimal.format(item.share_percent)} por cento`);row.append(heading,progress,element('small',`${decimal.format(item.area_ha)} ha`));bars.append(row);});
    $('experiment-error').classList.add('hidden');
  }catch(error){$('experiment-error').textContent=`Não foi possível carregar o resultado publicado: ${error.message}`;$('experiment-error').classList.remove('hidden');}
}
async function refreshSummary(){
  try{const d=await api('/api/v1/summary');
    $('stat-investigations').textContent=d.investigations;$('stat-evidence').textContent=d.evidence;
    $('stat-links').textContent=d.links;$('stat-journal').textContent=d.journal;
    $('connection').textContent='Núcleo local conectado';$('connection').parentElement.classList.remove('failed');
  }catch(e){$('connection').textContent='Núcleo indisponível';$('connection').parentElement.classList.add('failed');toast(e.message);}
}
async function refreshInvestigations(){
  const box=$('investigations-list');
  try{const [data,published]=await Promise.all([api('/api/v1/investigations'),api('/api/v1/investigations/published/exp-001')]);box.replaceChildren();
    const publication=element('article',null,'record published-record');const publicationButton=element('button',published.investigation.title);publicationButton.type='button';publicationButton.addEventListener('click',()=>navigate('experiment'));publication.append(element('span','PUBLICADA · PROTOCOLO EXECUTADO','tag published-tag'),publicationButton,element('p',published.question),element('small',`${published.investigation.location_ref} · Período investigado: ${formatPeriod(published.investigation.valid_start,published.investigation.valid_end)} · Execução: ${formatDate(published.execution.executed_at)}`));box.append(publication);
    if(!data.items.length)box.append(element('p','Nenhuma investigação local registrada. Você pode abrir uma nova pergunta.','empty-note'));
    data.items.forEach(item=>{
      const c=element('article',null,'record');const b=element('button',`#${item.id} · ${item.title}`);b.type='button';b.addEventListener('click',()=>openInvestigation(item.id));c.append(element('span','LOCAL · ABERTA','tag'),b,element('p',item.question),element('small',[item.location_ref&&`Recorte: ${item.location_ref}`,`Período: ${formatPeriod(item.valid_start,item.valid_end)}`,`Aberta em ${formatInstant(item.created_at)}`].filter(Boolean).join(' · ')));box.append(c);
    });
  }catch(e){empty(box,e.message);}
}
async function openInvestigation(id){
  try{const d=await api(`/api/v1/investigations/${id}`);activeInvestigation=id;
    $('dossier').classList.remove('hidden');$('dossier-title').textContent=`#${d.id} · ${d.title}`;$('dossier-question').textContent=d.question;
    $('dossier-period').textContent=formatPeriod(d.valid_start,d.valid_end);$('dossier-location').textContent=d.location_ref||'Não informado';$('dossier-created').textContent=formatInstant(d.created_at);
    const links=$('dossier-evidence');links.replaceChildren();
    if(!d.evidence_links.length)empty(links,'Nenhuma evidência vinculada. Relações não são inferidas automaticamente.');
    d.evidence_links.forEach(x=>{const c=element('div',null,'record');c.append(element('span',x.relation,'tag'),element('strong',`#${x.evidence_id} · ${x.source_name}`),element('p',x.statement),element('small',`Período referido: ${formatPeriod(x.valid_start,x.valid_end)} · ${observationText(x)}`),element('small',[x.location_ref&&`Recorte: ${x.location_ref}`,`Evidência registrada em ${formatInstant(x.inserted_at)}`,`Vínculo criado em ${formatInstant(x.created_at)}`].filter(Boolean).join(' · ')),element('small',`Estado: ${x.validation_status} · ${x.justification || 'Sem justificativa adicional'}`));links.append(c);});
    const journal=$('dossier-journal');journal.replaceChildren();
    if(!d.journal.length)empty(journal,'Diário ainda vazio. Registre perguntas e objeções.');
    d.journal.forEach(x=>{const c=element('div',null,'record');c.append(element('span',x.kind,'tag'),element('p',x.content),element('small',`${x.author_label} · registrado em ${formatInstant(x.created_at)}`));journal.append(c);});
    $('dossier').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){toast(e.message);}
}
async function refreshEvidence(){
  const box=$('evidence-list');
  try{const d=await api('/api/v1/evidence');box.replaceChildren();
    if(!d.items.length){empty(box,'Nenhuma evidência registrada. As fontes permanecem externas até ingestão explícita.');return;}
    d.items.forEach(x=>{const c=element('article',null,'record');c.append(element('span',`#${x.id} · ${x.kind}`,'tag'),element('strong',x.source_name),element('p',x.statement),element('small',`Fonte: ${x.source_ref} · ${x.validation_status}`),element('small',[x.location_ref&&`Recorte: ${x.location_ref}`,`Período referido: ${formatPeriod(x.valid_start,x.valid_end)}`,observationText(x),`Registrado em ${formatInstant(x.inserted_at)}`].filter(Boolean).join(' · ')));box.append(c);});
  }catch(e){empty(box,e.message);}
}
async function refreshAudit(){
  const box=$('audit-list');
  try{const d=await api('/api/v1/audit');box.replaceChildren();if(!d.items.length){empty(box,'Nenhuma operação registrada.');return;}
    d.items.forEach(x=>{const c=element('div',null,'record');c.append(element('strong',x.action),element('p',`${x.subject_type} #${x.subject_id}`),element('small',x.created_at));box.append(c);});
  }catch(e){empty(box,e.message);}
}
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.view)));
  document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.go)));
  $('menu').addEventListener('click',()=>{const open=$('sidebar').classList.toggle('open');$('scrim').hidden=!open;$('menu').setAttribute('aria-expanded',String(open));});
  $('scrim').addEventListener('click',()=>{$('sidebar').classList.remove('open');$('scrim').hidden=true;$('menu').setAttribute('aria-expanded','false');});
  $('refresh-investigations').addEventListener('click',refreshInvestigations);
  $('refresh-evidence').addEventListener('click',refreshEvidence);
  $('refresh-audit').addEventListener('click',refreshAudit);
  $('form-investigation').addEventListener('submit',e=>{e.preventDefault();postForm(e.currentTarget,'/api/v1/investigations','investigation-message',async d=>{await refreshInvestigations();await refreshSummary();await openInvestigation(d.id);});});
  $('form-evidence').addEventListener('submit',e=>{e.preventDefault();postForm(e.currentTarget,'/api/v1/evidence','evidence-message',async()=>{await refreshEvidence();await refreshSummary();},o=>({...o,observed_at:o.observed_at?new Date(o.observed_at).toISOString():'',observed_start:o.observed_start?new Date(o.observed_start).toISOString():'',observed_end:o.observed_end?new Date(o.observed_end).toISOString():''}));});
  $('form-link').addEventListener('submit',e=>{e.preventDefault();if(!activeInvestigation)return;postForm(e.currentTarget,`/api/v1/investigations/${activeInvestigation}/links`,'link-message',async()=>{await openInvestigation(activeInvestigation);await refreshSummary();},o=>({...o,evidence_id:Number(o.evidence_id)}));});
  $('form-journal').addEventListener('submit',e=>{e.preventDefault();if(!activeInvestigation)return;postForm(e.currentTarget,`/api/v1/investigations/${activeInvestigation}/journal`,'journal-message',async()=>{await openInvestigation(activeInvestigation);await refreshSummary();});});
  refreshSummary();
});
