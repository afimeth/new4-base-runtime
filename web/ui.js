let token,refreshVersion=0;
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
  const requestedCase=currentCase(),ticket=++refreshVersion;
  const c=await fetch('/api/capsule?case='+encodeURIComponent(requestedCase));const capsule=await c.json();if(!c.ok)throw Error(capsule.error);
  if(ticket!==refreshVersion||requestedCase!==currentCase())return;
  for(const id of ['tasks','events','sources','dictionary','map-milestones','map-parts','map-next','map-calls','map-changes'])el(id).replaceChildren();
  const map=capsule.project_map;
  el('map-phase').textContent='You are here · '+map.current_phase;
  el('map-counts').textContent=`${map.completion.done} of ${map.completion.total} workflows committed · ${map.completion.cancelled} cancelled`;
  for(const milestone of map.milestones){const m=node('div','','milestone');m.append(node('strong',String(milestone.count)),node('span',milestone.label));el('map-milestones').append(m);}
  for(const part of map.parts){const card=node('article','','map-part');card.dataset.status=part.label;card.append(node('h3',part.title),node('p',part.label,'badge'));if(part.reason)card.append(node('p',part.reason,'muted'));const last=part.receipts.at(-1);if(last){const link=node('a','Receipt #'+last.sequence);link.href='#receipt-'+last.sequence;card.append(link);}el('map-parts').append(card);}
  if(map.next_step){const next=map.next_step;el('map-next').append(node('p',next.title),node('p',next.reason,'muted'));if(next.action==='approve'){const review=node('a','Review exact result');review.href='#workflow-'+next.id;el('map-next').append(review);}else el('map-next').append(button(next.action==='execute'?'Create approved artifact':'Find / refresh context',()=>perform(next.action,next.id,{payload_hash:next.payload_hash})));}else el('map-next').append(node('p','No pending action. Start another workflow when needed.','muted'));
  if(!map.needs_your_call.length)el('map-calls').append(node('p','No approval waiting.','muted'));
  for(const call of map.needs_your_call)el('map-calls').append(node('p',call.title),node('p','Your explicit approval is required. No timeout grants it.','muted'));
  for(const change of map.recent_changes){const link=node('a','#'+change.sequence+' · '+change.kind+' · '+change.timestamp);link.href='#receipt-'+change.sequence;el('map-changes').append(link,node('br',''));}
  for(const task of capsule.tasks){
    const card=node('article','','task');card.id='workflow-'+task.id;card.append(node('h3',task.query),node('p',task.state,'badge'));
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
  for(const event of capsule.events){const item=node('li',event.sequence+' · '+event.kind+' · '+event.task);item.id='receipt-'+event.sequence;const proof=node('details','');proof.append(node('summary','Receipt evidence'),node('pre',JSON.stringify({hash:event.hash,previous:event.previous,timestamp:event.timestamp,data:JSON.parse(event.data)},null,2)));item.append(proof);el('events').append(item);}
  el('receipt').textContent=JSON.stringify(capsule.receipt,null,2);
}
el('start').onsubmit=async event=>{event.preventDefault();await perform('create','task_'+crypto.randomUUID().replaceAll('-',''),{query:el('query').value});};
el('import').onsubmit=async event=>{event.preventDefault();await perform('import',el('docid').value,{title:el('title').value,text:el('text').value});};
el('define').onsubmit=async event=>{event.preventDefault();await perform('define','definition',{term:el('term').value,meaning:el('meaning').value});};
el('export').onclick=()=>perform('export','capsule');el('case').onchange=()=>refresh().catch(e=>el('message').textContent=e.message);
el('scan').onclick=async()=>{try{const r=await fetch('/api/scan');el('scan-result').textContent=JSON.stringify(await r.json(),null,2);}catch(e){el('message').textContent=e.message;}};
(async()=>{try{const selected=new URLSearchParams(location.search).get('case');if(selected&&/^[a-zA-Z0-9_-]{1,64}$/.test(selected))el('case').value=selected;const r=await fetch('/api/session');token=(await r.json()).token;await refresh();}catch(e){el('message').textContent=e.message;}})();
