'use strict';
const $ = (id) => document.getElementById(id);
const names = {overview:'Visão geral',investigations:'Investigações',evidence:'Evidências',audit:'Integridade e limites'};
let activeInvestigation = null;
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
  document.querySelectorAll('.view').forEach(n=>n.classList.toggle('hidden',n.id!==`view-${name}`));
  document.querySelectorAll('[data-view]').forEach(n=>{n.classList.toggle('active',n.dataset.view===name);if(n.dataset.view===name)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});
  $('crumb-name').textContent=names[name];$('sidebar').classList.remove('open');$('scrim').hidden=true;$('menu').setAttribute('aria-expanded','false');
  if(name==='investigations')refreshInvestigations();
  if(name==='evidence')refreshEvidence();
  if(name==='audit')refreshAudit();
  $('main').focus({preventScroll:true});window.scrollTo({top:0,behavior:'auto'});
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
  try{const data=await api('/api/v1/investigations');box.replaceChildren();
    if(!data.items.length){empty(box,'Nenhuma investigação registrada. Comece pela pergunta.');return;}
    data.items.forEach(item=>{
      const c=element('article',null,'record');const b=element('button',`#${item.id} · ${item.title}`);b.type='button';b.addEventListener('click',()=>openInvestigation(item.id));c.append(b,element('p',item.question),element('small',[item.location_ref,item.created_at].filter(Boolean).join(' · ')));box.append(c);
    });
  }catch(e){empty(box,e.message);}
}
async function openInvestigation(id){
  try{const d=await api(`/api/v1/investigations/${id}`);activeInvestigation=id;
    $('dossier').classList.remove('hidden');$('dossier-title').textContent=`#${d.id} · ${d.title}`;$('dossier-question').textContent=d.question;
    const links=$('dossier-evidence');links.replaceChildren();
    if(!d.evidence_links.length)empty(links,'Nenhuma evidência vinculada. Relações não são inferidas automaticamente.');
    d.evidence_links.forEach(x=>{const c=element('div',null,'record');c.append(element('span',x.relation,'tag'),element('strong',`#${x.evidence_id} · ${x.source_name}`),element('p',x.statement),element('small',`Estado: ${x.validation_status} · ${x.justification || 'Sem justificativa adicional'}`));links.append(c);});
    const journal=$('dossier-journal');journal.replaceChildren();
    if(!d.journal.length)empty(journal,'Diário ainda vazio. Registre perguntas e objeções.');
    d.journal.forEach(x=>{const c=element('div',null,'record');c.append(element('span',x.kind,'tag'),element('p',x.content),element('small',`${x.author_label} · ${x.created_at}`));journal.append(c);});
    $('dossier').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){toast(e.message);}
}
async function refreshEvidence(){
  const box=$('evidence-list');
  try{const d=await api('/api/v1/evidence');box.replaceChildren();
    if(!d.items.length){empty(box,'Nenhuma evidência registrada. As fontes permanecem externas até ingestão explícita.');return;}
    d.items.forEach(x=>{const c=element('article',null,'record');c.append(element('span',`#${x.id} · ${x.kind}`,'tag'),element('strong',x.source_name),element('p',x.statement),element('small',`Fonte: ${x.source_ref} · ${x.validation_status}`),element('small',[x.location_ref,x.valid_start,x.valid_end].filter(Boolean).join(' · ')));box.append(c);});
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
  $('form-evidence').addEventListener('submit',e=>{e.preventDefault();postForm(e.currentTarget,'/api/v1/evidence','evidence-message',async()=>{await refreshEvidence();await refreshSummary();});});
  $('form-link').addEventListener('submit',e=>{e.preventDefault();if(!activeInvestigation)return;postForm(e.currentTarget,`/api/v1/investigations/${activeInvestigation}/links`,'link-message',async()=>{await openInvestigation(activeInvestigation);await refreshSummary();},o=>({...o,evidence_id:Number(o.evidence_id)}));});
  $('form-journal').addEventListener('submit',e=>{e.preventDefault();if(!activeInvestigation)return;postForm(e.currentTarget,`/api/v1/investigations/${activeInvestigation}/journal`,'journal-message',async()=>{await openInvestigation(activeInvestigation);await refreshSummary();});});
  refreshSummary();
});
