"""Project-map lens derived from a consistent case snapshot; no second state."""
import json
from runtime import digest


def project_map(tasks,events,documents,dictionary_hash):
    generation=digest(documents);parts=[];calls=[]
    for task in tasks:
        payload=task['payload'];state=task['state'];action=None;reason=None
        if state=='DONE':label='Done'
        elif state=='CANCELLED':label='Cancelled'
        elif state=='NEW':label='Not started';action='prepare';reason='Find the relevant context.'
        elif state=='ABSTAINED':label='Hold';action='prepare';reason=payload.get('hold_reason') or 'Add a relevant source or clarify the request.'
        elif payload['corpus_hash']!=generation or payload.get('dictionary_hash')!=dictionary_hash:
            label='Context changed';action='prepare';reason='Refresh the proposal; previous approval cannot authorize new source meaning.'
        elif task['approval'] and task['approval']['payload_hash']==task['payload_hash']:
            label='Ready';action='execute';reason='Create the approved local artifact.'
        else:
            label='Awaiting approval';action='approve';reason='Review this exact result before any artifact is created.'
            calls.append({'task_id':task['id'],'title':task['query'],'payload_hash':task['payload_hash'],'reason':reason,'timeout_grants_authority':False})
        receipts=[{'sequence':e['sequence'],'kind':e['kind'],'hash':e['hash'],'timestamp':e['timestamp']} for e in events if e['task']==task['id']]
        parts.append({'id':task['id'],'title':task['query'],'state':state,'label':label,'action':action,'reason':reason,'payload_hash':task['payload_hash'],'receipts':receipts})
    priority={'Ready':0,'Not started':1,'Context changed':2,'Awaiting approval':3,'Hold':4}
    candidates=[p for p in parts if p['action']]
    candidates.sort(key=lambda p:(priority[p['label']],p['id']))
    next_step=candidates[0] if candidates else None
    milestones=[{'id':'sources','label':'Sources','count':len(documents)},
                {'id':'context','label':'Prepared','count':sum(bool(t['payload']) for t in tasks)},
                {'id':'review','label':'Reviewed','count':sum(bool(t['approval']) for t in tasks)},
                {'id':'artifacts','label':'Committed','count':sum(t['state']=='DONE' for t in tasks)}]
    changes=[{'sequence':e['sequence'],'task_id':e['task'],'kind':e['kind'],'timestamp':e['timestamp'],'receipt_hash':e['hash']} for e in events[-8:]]
    return {'schema':'project-map/1','current_phase':next_step['label'] if next_step else ('Complete' if tasks else 'Start a case'),
        'parts':parts,'milestones':milestones,'next_step':next_step,'needs_your_call':calls,'recent_changes':changes,
        'completion':{'done':sum(t['state']=='DONE' for t in tasks),'total':len(tasks),'cancelled':sum(t['state']=='CANCELLED' for t in tasks),'percent':None,'basis':'Task counts; no subjective progress estimate'},
        'scope':'Operational workflow projection, not an inferred product roadmap','authority':'Owner approval remains explicit; elapsed time never grants approval'}
