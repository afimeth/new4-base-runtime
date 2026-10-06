"""Case-scoped dictionary/index/topology and lenses over one durable substrate."""
import json
from pathlib import Path
import re
from runtime import ROOT, digest, now


def capsule(runtime,case_id='demo'):
    with runtime.snapshot():return _capsule(runtime,case_id)


def _capsule(runtime,case_id):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',case_id):raise ValueError('INVALID_CASE_ID')
    docs=runtime.corpus(case_id)
    view=runtime.view();tasks=[t for t in view['tasks'] if t['case_id']==case_id]
    base=json.loads((ROOT/'contracts/dictionary.json').read_text(encoding='utf8'))
    dictionary=[{**entry,'scope':'REPOSITORY_DESIGN','definition_role':base['role']} for entry in base['entries']]
    dictionary += [{**dict(row),'scope':case_id,'definition_role':'LOCAL_OPERATOR_DEFINITION'} for row in runtime.db.execute('SELECT term,meaning,recorded_at FROM dictionary WHERE case_id=? ORDER BY term',(case_id,))]
    postings={};nodes=[];edges=[];ids={d['id'] for d in docs};gaps=[]
    for doc in docs:
        nodes.append({'id':'document:'+doc['id'],'kind':'SOURCE','label':doc['title'],'source_hash':digest(doc)})
        for match in re.finditer(r'\w+',doc['text'],re.UNICODE):
            spelling=match.group();word='word:'+digest(spelling)
            entry=postings.setdefault(spelling,{'id':word,'spelling':spelling,'lookup':spelling.casefold(),'mentions':[],'meaning_status':'LEXICAL_NOT_DEFINED','semantic_confidence':None})
            entry['mentions'].append({'document':doc['id'],'source_hash':digest(doc),'start':match.start(),'end':match.end(),'offset_unit':'Unicode code points; end exclusive'})
        for target in re.findall(r'\[\[([\w-]+)\]\]',doc['text']):
            if target in ids:edges.append({'from':'document:'+doc['id'],'to':'document:'+target,'relation':'EXPLICIT_DOCUMENT_REFERENCE','semantic_confidence':None})
            else:gaps.append({'source':doc['id'],'target':target,'status':'UNRESOLVED_REFERENCE'})
    for spelling,entry in sorted(postings.items()):
        nodes.append({'id':entry['id'],'label':spelling,'kind':'LEXEME'})
        for identifier in sorted({m['document'] for m in entry['mentions']}):edges.append({'from':'document:'+identifier,'to':entry['id'],'relation':'CONTAINS_EXACT_WORD','semantic_confidence':None})
    for entry in dictionary:
        identifier='meaning:'+digest([entry['scope'],entry['term'],entry['meaning']])
        nodes.append({'id':identifier,'label':entry['term'],'kind':'EXPLICIT_MEANING','definition_role':entry['definition_role']})
        if entry['term'] in postings:edges.append({'from':postings[entry['term']]['id'],'to':identifier,'relation':'HAS_SCOPED_DEFINITION','semantic_confidence':None})
    providers=[{'id':'provider:local-python','kind':'PROVIDER_AGENT','tools':['corpus.retrieve','feed.local','feed.cloud','artifact.create'],'cloud_model':False},
               {'id':'provider:local-go','kind':'PROVIDER_AGENT','tools':['onion.parse','search.rank','math.sum','graph.route'],'cloud_model':False}]
    for provider in providers:nodes.append({**provider,'label':provider['id']})
    for worker in view['workers']:
        node={'id':'worker:'+worker['id'],'kind':'WORKER_AGENT','label':worker['id']};nodes.append(node)
        edges.append({'from':node['id'],'to':'provider:local-go' if worker['id']=='go-onion' else 'provider:local-python','relation':'USES_PROVIDER'})
    for task in tasks:
        identifier='task:'+task['id'];nodes.append({'id':identifier,'kind':'TASK','label':task['query'],'state':task['state']})
        if task['payload']:
            edges.append({'from':identifier,'to':'worker:go-onion','relation':'PARSED_BY'})
            for source in task['payload']['sources']:
                # Historical task sources remain identifiable after a current-source revision.
                source_node='document:'+source['id']
                if not any(n['id']==source_node for n in nodes):nodes.append({'id':source_node,'kind':'HISTORICAL_SOURCE','label':source['id']})
                edges.append({'from':identifier,'to':source_node,'relation':'RETRIEVED_FROM','captured_source_hash':source['hash']})
    lenses={'engineering':{'kind':'ENGINEERING_LENS','state_effect_boundary':'SINGLE_SQLITE_TRANSACTION','worker_memory':'STATELESS_PER_CALL','provider_isolation':'LOGICAL_PROTOCOL_BOUNDARY_NOT_OS_SANDBOX','external_effects':False},
            'qa':{'kind':'QA_LENS','receipt':view['receipt'],'semantic_accuracy':None,'independent_review':None,'test_evidence':'evidence/local-eval.json'}}
    for name,lens in lenses.items():nodes.append({'id':'lens:'+name,'kind':lens['kind'],'label':name})
    body={'schema':'work-capsule/1','case_id':case_id,'sources':[{'id':d['id'],'title':d['title'],'hash':digest(d)} for d in docs],
          'tasks':tasks,'dictionary':dictionary,'semantic_index':list(postings.values()),
          'topology':{'nodes':nodes,'edges':edges,'gaps':gaps},'worker_agents':view['workers'],'provider_agents':providers,'lenses':lenses,
          'authority_boundary':'LOCAL_CONTEXT_PROJECTION_NOT_TRUTH_OR_VERIFIED_OWNER_IDENTITY','embedding_model':None,'semantic_confidence':None}
    body['architecture']=json.loads((ROOT/'contracts/room.json').read_text(encoding='utf8'))
    body['receipt']=view['receipt']
    body['memory']=[dict(r) for r in runtime.db.execute('SELECT id,revision,source,source_hash,status,role FROM memory WHERE case_id=? ORDER BY id,revision',(case_id,))]
    task_ids={t['id'] for t in tasks}
    body['events']=[e for e in view['events'] if e['task'] in task_ids or json.loads(e['data']).get('case_id')==case_id]
    body['context_quality']={'case_sources':len(docs),'explicit_reference_gaps':len(gaps),'prepared_workflows':sum(t['payload'] is not None for t in tasks),'current_source_bound_workflows':sum(t['payload'] is not None and t['payload']['corpus_hash']==digest(docs) for t in tasks),'semantic_relevance':None,'user_utility':None}
    return {**body,'version':digest(body)}


def export(runtime,case_id='demo'):
    value=capsule(runtime,case_id)
    folder=ROOT/'.state'/'work'/case_id/value['version']
    folder.mkdir(parents=True,exist_ok=True)
    parts={'capsule.json':value,'dictionary.json':value['dictionary'],'semantic-index.json':value['semantic_index'],'topology.json':value['topology'],'lenses.json':value['lenses']}
    for name,part in parts.items():
        content=json.dumps(part,ensure_ascii=False,indent=2)+'\n';path=folder/name
        if path.exists() and path.read_text(encoding='utf8')!=content:raise ValueError('PROJECTION_CONFLICT')
        path.write_text(content,encoding='utf8',newline='\n')
    return {'schema':'work-folder/1','case_id':case_id,'capsule_version':value['version'],'folder':str(folder),'role':'REPRODUCIBLE_PROJECTION_NOT_SECOND_AUTHORITY','files':list(parts)}
