let token;
const el=id=>document.getElementById(id);
function node(tag,text,cls){const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n;}
const currentCase=()=>el('case').value;
async function act(action,id,extra={}){
  const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({action,id,case_id:currentCase(),...extra})});
  const value=await r.json();if(!r.ok)throw Error(value.error);await refresh();return value;
}
async function perform(action,id,extra){try{const value=await act(action,id,extra);el('message').textContent=value.folder?'Exported: '+value.folder:'Saved: '+action;return value;}catch(e){el('message').textContent=e.message;}}
function button(label,action){const b=node('button',label);b.type='button';b.onclick=action;return b;}
async function refresh(){
  const r=await fetch('/api/state');const view=await r.json();if(!r.ok)throw Error(view.error);
  const c=await fetch('/api/capsule?case='+encodeURIComponent(currentCase()));const capsule=await c.json();if(!c.ok)throw Error(capsule.error);
  for(const id of ['tasks','events','sources','dictionary'])el(id).replaceChildren();
  for(const task of capsule.tasks){
    const card=node('article','','task');card.append(node('h3',task.query),node('p',task.state,'badge'));
    if(task.payload){
      card.append(node('pre',task.payload.hold_reason||task.payload.draft||'No matching source. Add a note or refine the request.'));
      for(const source of task.payload.sources){const line=node('div','','row');line.append(node('p',source.id+' · '+source.hash.slice(0,16),'muted'),button('Helpful',()=>perform('feedback',task.id,{source:source.id,rating:1})),button('Not helpful',()=>perform('feedback',task.id,{source:source.id,rating:-1})));card.append(line);}
      const detail=node('details','');detail.append(node('summary','How this request was resolved'),node('pre',JSON.stringify({onion:task.payload.onion,ranking:task.payload.ranking,coverage:task.payload.retrieval_scope},null,2)));card.append(detail);
    }
    const buttons=node('div','','row');
    const choices=task.state==='NEW'?[['prepare','Find my context']]:task.state==='AWAITING_APPROVAL'?(task.approval?[['execute','Create local artifact'],['prepare','Refresh context']]:[['approve','Approve this result'],['prepare','Refresh context']]):task.state==='ABSTAINED'?[['prepare','Try current sources']]:[];
    if(!['DONE','CANCELLED'].includes(task.state))choices.push(['cancel','Cancel']);
    for(const [action,label] of choices){const b=node('button',label);b.type='button';b.onclick=()=>perform(action,task.id,{payload_hash:task.payload_hash});buttons.append(b);}
    if(task.state==='DONE')card.append(node('p','Local artifact committed. Repeated execution returns the same artifact.'));
    card.append(buttons);el('tasks').append(card);
  }
  for(const source of capsule.sources)el('sources').append(node('p',source.id+' · '+source.title,'muted'));
  for(const item of capsule.dictionary){const d=node('p','');d.append(node('strong',item.term+' — '),document.createTextNode(item.meaning));el('dictionary').append(d);}
  const labels=Object.fromEntries(capsule.topology.nodes.map(n=>[n.id,n.label]));
  el('graph').textContent=JSON.stringify({nodes:capsule.topology.nodes.length,links:capsule.topology.edges.length,word_entries:capsule.semantic_index.length,relations:capsule.topology.edges.filter(e=>e.relation!=='CONTAINS_EXACT_WORD').map(e=>({from:labels[e.from],relation:e.relation,to:labels[e.to]})),gaps:capsule.topology.gaps},null,2);
  el('lenses').textContent=JSON.stringify({architecture:capsule.architecture,context_quality:capsule.context_quality,workers:capsule.worker_agents,providers:capsule.provider_agents,lenses:capsule.lenses},null,2);
  el('capsule-summary').textContent=`${capsule.sources.length} source${capsule.sources.length===1?'':'s'} · ${capsule.tasks.length} workflow${capsule.tasks.length===1?'':'s'} · ${capsule.semantic_index.length} exact word entries. Version ${capsule.version.slice(0,12)}.`;
  for(const event of capsule.events)el('events').append(node('li',event.sequence+' · '+event.kind+' · '+event.task));
  el('receipt').textContent=JSON.stringify(capsule.receipt,null,2);
}
el('start').onsubmit=async event=>{event.preventDefault();await perform('create','task_'+crypto.randomUUID().replaceAll('-',''),{query:el('query').value});};
el('import').onsubmit=async event=>{event.preventDefault();await perform('import',el('docid').value,{title:el('title').value,text:el('text').value});};
el('define').onsubmit=async event=>{event.preventDefault();await perform('define','definition',{term:el('term').value,meaning:el('meaning').value});};
el('export').onclick=()=>perform('export','capsule');el('case').onchange=()=>refresh().catch(e=>el('message').textContent=e.message);
el('scan').onclick=async()=>{try{const r=await fetch('/api/scan');el('scan-result').textContent=JSON.stringify(await r.json(),null,2);}catch(e){el('message').textContent=e.message;}};
(async()=>{try{const r=await fetch('/api/session');token=(await r.json()).token;await refresh();}catch(e){el('message').textContent=e.message;}})();
