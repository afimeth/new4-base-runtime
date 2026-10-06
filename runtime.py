"""A local context-to-action runtime. No model calls or external effects."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from workers import call
from workers import binary

ROOT = Path(__file__).resolve().parent
POLICY = {"version": "local-artifact/1", "allowed_tool": "artifact.create", "approval": "exact_payload_hash", "external_effects": False}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


class Rejected(ValueError):
    """Stable machine-readable failure code in str(exception)."""


class Runtime:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, query TEXT NOT NULL,
            state TEXT NOT NULL, payload TEXT, payload_hash TEXT, corpus_hash TEXT);
          CREATE TABLE IF NOT EXISTS approvals(task TEXT PRIMARY KEY REFERENCES tasks(id),
            payload_hash TEXT NOT NULL, operator TEXT NOT NULL, timestamp TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS artifacts(task TEXT PRIMARY KEY REFERENCES tasks(id),
            payload_hash TEXT NOT NULL, body TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY, task TEXT NOT NULL,
            kind TEXT NOT NULL, timestamp TEXT NOT NULL, data TEXT NOT NULL,
            previous TEXT NOT NULL, hash TEXT UNIQUE NOT NULL);
          CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, title TEXT NOT NULL,
            text TEXT NOT NULL, hash TEXT NOT NULL, recorded_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS sources(id TEXT NOT NULL, case_id TEXT NOT NULL,
            title TEXT NOT NULL, text TEXT NOT NULL, hash TEXT NOT NULL, recorded_at TEXT NOT NULL,
            provenance TEXT NOT NULL, PRIMARY KEY(id,case_id));
          CREATE TABLE IF NOT EXISTS feedback(task TEXT NOT NULL, source TEXT NOT NULL,
            case_id TEXT NOT NULL, query_key TEXT NOT NULL, source_hash TEXT NOT NULL,
            rating INTEGER NOT NULL, recorded_at TEXT NOT NULL, PRIMARY KEY(task,source));
          CREATE TABLE IF NOT EXISTS dictionary(case_id TEXT NOT NULL, term TEXT NOT NULL,
            meaning TEXT NOT NULL,recorded_at TEXT NOT NULL, PRIMARY KEY(case_id,term));
        """)
        if 'case_id' not in {r['name'] for r in self.db.execute('PRAGMA table_info(tasks)')}:
            self.db.execute("ALTER TABLE tasks ADD COLUMN case_id TEXT NOT NULL DEFAULT 'demo'")

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def event(self, task, kind, data):
        last = self.db.execute("SELECT sequence,hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        record = {"sequence": last[0]+1 if last else 1, "task": task, "kind": kind,
                  "timestamp": now(), "data": data, "previous": last[1] if last else "0"*64}
        self.db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?)", (
            record['sequence'], task, kind, record['timestamp'], encoded(data), record['previous'], digest(record)))

    def task(self, identifier):
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise Rejected("TASK_NOT_FOUND")
        return dict(row)

    def create(self, identifier, query, case_id='demo'):
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", identifier):
            raise Rejected("INVALID_TASK_ID")
        if not isinstance(query, str) or not query.strip() or len(query)>2000:
            raise Rejected("INVALID_QUERY")
        if not isinstance(case_id,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',case_id):raise Rejected('INVALID_CASE_ID')
        with self.transaction():
            old = self.db.execute("SELECT query,case_id FROM tasks WHERE id=?", (identifier,)).fetchone()
            if old:
                if old[0] != query or old[1]!=case_id:
                    raise Rejected("IDEMPOTENCY_CONFLICT")
                return self.task(identifier)
            self.db.execute("INSERT INTO tasks(id,query,state,case_id) VALUES(?,?,?,?)", (identifier, query, "NEW",case_id))
            self.event(identifier, "CREATED", {"query": query,'case_id':case_id})
        return self.task(identifier)

    @staticmethod
    def documents(path=None):
        items = json.loads(Path(path or ROOT/'fixtures/documents.json').read_text(encoding='utf-8'))
        if not isinstance(items, list) or len(items)>1000:
            raise Rejected("INVALID_CORPUS")
        ids = set()
        for item in items:
            if not isinstance(item, dict) or set(item)!={'id','title','text'} or any(not isinstance(v,str) or len(v)>8000 for v in item.values()) or not item['id'] or item['id'] in ids:
                raise Rejected("INVALID_CORPUS")
            ids.add(item['id'])
        return items

    def prepare(self, identifier, documents=None):
        # Validate caller-supplied fixture data through the same parser contract.
        docs = self.corpus(self.task(identifier)['case_id']) if documents is None else json.loads(encoded(documents))
        if not isinstance(docs,list) or len(docs)>1000 or any(not isinstance(d,dict) or set(d)!={'id','title','text'} or any(not isinstance(v,str) or len(v)>8000 for v in d.values()) or not d['id'] for d in docs) or len({d['id'] for d in docs})!=len(docs):
            raise Rejected("INVALID_CORPUS")
        generation = digest(docs)
        with self.transaction():
            task = self.task(identifier)
            if task['state'] in ('DONE','CANCELLED'):
                raise Rejected("TERMINAL_TASK")
            try:onion=call('onion.parse',{'text':task['query']})
            except ValueError as exc:raise Rejected(str(exc)) from exc
            tokens = set(onion['keywords'])
            meaning_expansions=[]
            for entry in self.db.execute('SELECT term,meaning FROM dictionary WHERE case_id=? ORDER BY term',(task['case_id'],)):
                if entry['term'].casefold() in task['query'].casefold():
                    expanded=set(re.findall(r'\w+',entry['meaning'].casefold()))
                    tokens.update(expanded)
                    meaning_expansions.append({'term':entry['term'],'meaning':entry['meaning'],'role':'EXPLICIT_CASE_DEFINITION_NOT_MODEL_INFERENCE'})
            candidates=[];size=0
            for doc in docs:
                overlap = tokens & set(re.findall(r"\w+", (doc['title']+' '+doc['text']).casefold()))
                if not overlap:continue
                cost=len(encoded(doc).encode())
                if size+cost>44000 or len(candidates)>=32:continue
                size+=cost;candidates.append(doc)
            query_key=digest(sorted(tokens));feedback={}
            for row in self.db.execute('SELECT source,source_hash,rating FROM feedback WHERE case_id=? AND query_key=? ORDER BY recorded_at',(task['case_id'],query_key)):
                if any(d['id']==row['source'] and digest(d)==row['source_hash'] for d in candidates):feedback[row['source']]=row['rating']
            try:ranked=call('search.rank',{'query':sorted(tokens),'documents':candidates,'feedback':feedback})
            except ValueError as exc:raise Rejected(str(exc)) from exc
            selected=[next(d for d in candidates if d['id']==r['id']) for r in ranked[:3]]
            computed=None;hold_reason=None
            try:
                if onion['frame']=='math':
                    computed=call('math.sum',{'text':task['query']});selected=[]
                elif onion['frame']=='topology':
                    matched=re.search(r'\bfrom\s+([\w-]+)\s+to\s+([\w-]+)',task['query'],re.I)
                    if not matched:raise ValueError('USE_ROUTE_FROM_NODE_TO_NODE')
                    graph_edges=[]
                    for doc in docs:
                        for target in re.findall(r'\[\[([\w-]+)\]\]',doc['text']):graph_edges.append([doc['id'],target])
                    computed=call('graph.route',{'nodes':[d['id'] for d in docs],'edges':graph_edges,'from':matched[1],'to':matched[2]})
                    selected=[d for d in docs if d['id'] in computed['path']]
            except ValueError as exc:hold_reason=str(exc)
            payload = {"schema":"artifact/1", "tool":"artifact.create", "query":task['query'],
                "policy_hash":digest(POLICY), "corpus_hash":generation, "planner":"deterministic-extractive/1",
                "case_id":task['case_id'],"worker_protocol":"worker-request/1",
                "meaning_expansions":meaning_expansions,"dictionary_hash":self.definition_version(task['case_id']),
                "ranking":ranked,"query_key":query_key,"retrieval_scope":{'candidate_limit':32,'input_bytes_limit':44000,'candidate_count':len(candidates),'source_count':len(docs),'coverage':'BOUNDED_LEXICAL_CANDIDATES_NOT_FULL_SEMANTIC_SEARCH'},
                "semantic_confidence":None, "sources":[{"id":d['id'],"hash":digest(d)} for d in selected],
                "onion":onion,"computation":computed,"hold_reason":hold_reason,
                "draft":encoded(computed) if computed is not None else "\n\n".join(d['title']+'\n'+d['text'] for d in selected)}
            h = digest(payload)
            state = 'AWAITING_APPROVAL' if (selected or computed is not None) and not hold_reason else 'ABSTAINED'
            if task['payload_hash'] == h and task['state'] == state:
                return self.task(identifier)
            self.db.execute("DELETE FROM approvals WHERE task=?", (identifier,))
            self.db.execute("UPDATE tasks SET state=?,payload=?,payload_hash=?,corpus_hash=? WHERE id=?", (state, encoded(payload),h,generation,identifier))
            self.event(identifier, "PREPARED" if selected else "ABSTAINED", {"payload_hash":h,"source_ids":[d['id'] for d in selected],"planner":payload['planner']})
        return self.task(identifier)

    def approve(self, identifier, payload_hash, operator='local-operator'):
        if not isinstance(operator,str) or not 1<=len(operator)<=80:
            raise Rejected("INVALID_OPERATOR")
        with self.transaction():
            task = self.task(identifier)
            if task['state'] != 'AWAITING_APPROVAL' or task['payload_hash'] != payload_hash:
                raise Rejected("STALE_OR_INELIGIBLE_APPROVAL")
            old = self.db.execute("SELECT * FROM approvals WHERE task=?",(identifier,)).fetchone()
            if old and old['payload_hash']==payload_hash and old['operator']==operator:
                return self.task(identifier)
            self.db.execute("INSERT OR REPLACE INTO approvals VALUES(?,?,?,?)",(identifier,payload_hash,operator,now()))
            self.event(identifier,"APPROVED",{"payload_hash":payload_hash,"operator":operator,"identity_assurance":"LOCAL_DECLARATION_NOT_VERIFIED_IDENTITY"})
        return self.task(identifier)

    def cancel(self, identifier):
        with self.transaction():
            task=self.task(identifier)
            if task['state']=='DONE':
                raise Rejected("ALREADY_COMMITTED")
            if task['state']=='CANCELLED':
                return task
            self.db.execute("DELETE FROM approvals WHERE task=?",(identifier,))
            self.db.execute("UPDATE tasks SET state='CANCELLED' WHERE id=?",(identifier,))
            self.event(identifier,'CANCELLED',{})
        return self.task(identifier)

    def execute(self, identifier, documents=None, fault=None):
        docs=self.corpus(self.task(identifier)['case_id']) if documents is None else documents
        with self.transaction():
            task=self.task(identifier)
            if task['state']=='DONE':
                stored=self.db.execute('SELECT * FROM artifacts WHERE task=?',(identifier,)).fetchone()
                if stored is None or stored['payload_hash']!=task['payload_hash'] or digest(json.loads(stored['body']))!=stored['payload_hash']:
                    raise Rejected('ARTIFACT_INTEGRITY_FAILURE')
                return task
            if task['state']!='AWAITING_APPROVAL':
                raise Rejected('TASK_NOT_EXECUTABLE')
            payload=json.loads(task['payload'])
            if digest(payload)!=task['payload_hash'] or payload['policy_hash']!=digest(POLICY) or payload['tool']!=POLICY['allowed_tool']:
                raise Rejected('PAYLOAD_OR_POLICY_CHANGED')
            if digest(docs)!=task['corpus_hash']:
                raise Rejected('SOURCE_CHANGED_REPREPARE_REQUIRED')
            if payload.get('dictionary_hash')!=self.definition_version(task['case_id']):
                raise Rejected('DEFINITION_CHANGED_REPREPARE_REQUIRED')
            approval=self.db.execute('SELECT payload_hash FROM approvals WHERE task=?',(identifier,)).fetchone()
            if approval is None or approval[0]!=task['payload_hash']:
                raise Rejected('APPROVAL_REQUIRED')
            # The effect IS the artifact row in this database, not an external send.
            self.db.execute('INSERT INTO artifacts VALUES(?,?,?)',(identifier,task['payload_hash'],task['payload']))
            if fault:
                fault('after_artifact_before_commit')
            self.db.execute("UPDATE tasks SET state='DONE' WHERE id=?",(identifier,))
            self.event(identifier,'COMMITTED',{'payload_hash':task['payload_hash'],'tool':payload['tool']})
        if fault:
            fault('after_commit_before_ack')
        return self.task(identifier)

    def verify(self):
        previous='0'*64
        count=0
        for row in self.db.execute('SELECT * FROM events ORDER BY sequence'):
            count+=1
            body={'sequence':row['sequence'],'task':row['task'],'kind':row['kind'],'timestamp':row['timestamp'],'data':json.loads(row['data']),'previous':row['previous']}
            if row['sequence']!=count or row['previous']!=previous or digest(body)!=row['hash']:
                raise Rejected('RECEIPT_CHAIN_INVALID')
            previous=row['hash']
        for task in self.db.execute('SELECT * FROM tasks'):
            artifact=self.db.execute('SELECT * FROM artifacts WHERE task=?',(task['id'],)).fetchone()
            if bool(artifact)!=(task['state']=='DONE'):
                raise Rejected('STATE_EFFECT_INVARIANT_BROKEN')
            if artifact and (artifact['payload_hash']!=task['payload_hash'] or digest(json.loads(artifact['body']))!=artifact['payload_hash']):
                raise Rejected('ARTIFACT_INTEGRITY_FAILURE')
        return {'schema':'receipt-verification/1','events':count,'head':previous,'chain':'VERIFIED_LOCAL','external_anchor':None,'identity_assurance':'LOCAL_DECLARATION','database_integrity':self.db.execute('PRAGMA integrity_check').fetchone()[0]}

    def view(self):
        tasks=[dict(row) for row in self.db.execute('SELECT * FROM tasks ORDER BY id')]
        for task in tasks:
            task['payload']=json.loads(task['payload']) if task['payload'] else None
            approval=self.db.execute('SELECT operator,timestamp,payload_hash FROM approvals WHERE task=?',(task['id'],)).fetchone()
            task['approval']=dict(approval) if approval else None
        return {'schema':'runtime-view/1','tasks':tasks,'documents':[{'id':d['id'],'case_id':case_id,'title':d['title'],'hash':digest(d)} for case_id in sorted({'demo'}|{row[0] for row in self.db.execute('SELECT DISTINCT case_id FROM sources')}) for d in self.corpus(case_id)],
            'workers':[{'id':'python-context','zone':'context and durable control','tools':['corpus.retrieve','artifact.create'],'state':'AVAILABLE'},
                       {'id':'go-onion','zone':'language, math and topology','tools':['onion.parse','search.rank','math.sum','graph.route'],'state':'BUILT_LOCAL' if binary().exists() else 'NOT_BUILT','lifecycle':'ONE_PROCESS_PER_CALL; NO_CASE_MEMORY'}],
            'events':[dict(r) for r in self.db.execute('SELECT * FROM events ORDER BY sequence')], 'artifacts':[dict(r) for r in self.db.execute('SELECT * FROM artifacts ORDER BY task')],'receipt':self.verify(),'policy':POLICY,'model_calls':0}

    def corpus(self,case_id='demo'):
        docs={d['id']:d for d in self.documents()} if case_id=='demo' else {}
        for row in self.db.execute('SELECT id,title,text FROM sources WHERE case_id=? ORDER BY id',(case_id,)):docs[row['id']]=dict(row)
        return list(docs.values())

    def import_document(self,identifier,title,text,case_id='demo',provenance=None):
        if not isinstance(identifier,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',identifier) or not isinstance(title,str) or not 1<=len(title)<=160 or not isinstance(text,str) or not 1<=len(text)<=8000:
            raise Rejected('INVALID_DOCUMENT')
        if not isinstance(case_id,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',case_id):raise Rejected('INVALID_CASE_ID')
        doc={'id':identifier,'title':title,'text':text};h=digest(doc)
        with self.transaction():
            old=self.db.execute('SELECT hash FROM sources WHERE id=? AND case_id=?',(identifier,case_id)).fetchone()
            if old and old[0]==h:return {'id':identifier,'hash':h,'status':'UNCHANGED'}
            self.db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?,?,?)',(identifier,case_id,title,text,h,now(),encoded(provenance or {'kind':'LOCAL_OPERATOR_TEXT'})))
            self.event('document:'+identifier,'SOURCE_REVISED',{'id':identifier,'case_id':case_id,'hash':h,'previous_hash':old[0] if old else None,'provenance':provenance or {'kind':'LOCAL_OPERATOR_TEXT'}})
        return {'id':identifier,'hash':h,'status':'IMPORTED_LOCAL_ONLY'}

    def feedback(self,identifier,source,rating):
        if type(rating) is not int or rating not in (-1,1):raise Rejected('INVALID_FEEDBACK')
        with self.transaction():
            task=self.task(identifier)
            if not task['payload']:raise Rejected('NO_PREPARED_CONTEXT')
            payload=json.loads(task['payload'])
            selected=next((s for s in payload['sources'] if s['id']==source),None)
            if selected is None:raise Rejected('FEEDBACK_SOURCE_NOT_SELECTED')
            self.db.execute('INSERT OR REPLACE INTO feedback VALUES(?,?,?,?,?,?,?)',(identifier,source,task['case_id'],payload['query_key'],selected['hash'],rating,now()))
            self.event(identifier,'FEEDBACK',{'source':source,'rating':rating,'scope':'SAME_CASE_QUERY_AND_SOURCE_BYTES_ONLY'})
        return {'status':'FEEDBACK_RECORDED','source':source,'rating':rating}

    def define(self,case_id,term,meaning):
        if not isinstance(case_id,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',case_id) or not isinstance(term,str) or not 1<=len(term)<=120 or not isinstance(meaning,str) or not 1<=len(meaning)<=2000:raise Rejected('INVALID_DEFINITION')
        with self.transaction():
            self.db.execute('INSERT OR REPLACE INTO dictionary VALUES(?,?,?,?)',(case_id,term,meaning,now()))
            self.event('dictionary:'+case_id,'DEFINED',{'term':term,'meaning':meaning,'role':'LOCAL_OPERATOR_DEFINITION'})
        return {'status':'DEFINED_LOCAL','case_id':case_id,'term':term}

    def definition_version(self,case_id):
        return digest([dict(r) for r in self.db.execute('SELECT term,meaning FROM dictionary WHERE case_id=? ORDER BY term',(case_id,))])
