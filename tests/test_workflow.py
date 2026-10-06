import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app import serve
from runtime import Runtime, Rejected, ROOT, digest


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from workers import ensure_worker
        ensure_worker()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'runtime.sqlite'
        self.rt=Runtime(self.path)

    def tearDown(self):
        self.rt.close();self.tmp.cleanup()

    def ready(self,identifier='task',query='release reviewer rollback'):
        self.rt.create(identifier,query)
        task=self.rt.prepare(identifier)
        self.rt.approve(identifier,task['payload_hash'])
        return task

    def reject(self,code,function,*args,**kwargs):
        with self.assertRaisesRegex(Rejected,'^'+code+'$'):
            function(*args,**kwargs)

    def test_end_to_end_source_bound_artifact(self):
        task=self.ready()
        self.assertEqual([s['id'] for s in json.loads(task['payload'])['sources']],['release-policy'])
        self.assertEqual(self.rt.execute('task')['state'],'DONE')
        view=self.rt.view()
        self.assertEqual(len(view['artifacts']),1)
        self.assertEqual(view['receipt']['events'],4)
        self.assertIsNone(json.loads(view['artifacts'][0]['body'])['semantic_confidence'])

    def test_approval_denial_and_positive_control(self):
        self.rt.create('task','invoice supplier total')
        task=self.rt.prepare('task')
        self.reject('APPROVAL_REQUIRED',self.rt.execute,'task')
        self.assertEqual(self.rt.view()['artifacts'],[])
        self.rt.approve('task',task['payload_hash'])
        self.assertEqual(self.rt.execute('task')['state'],'DONE')

    def test_source_change_invalidates_old_approval(self):
        task=self.ready()
        docs=self.rt.documents();docs[0]['text']+=' Updated policy requires a checklist.'
        self.reject('SOURCE_CHANGED_REPREPARE_REQUIRED',self.rt.execute,'task',docs)
        newer=self.rt.prepare('task',docs)
        self.assertNotEqual(task['payload_hash'],newer['payload_hash'])
        self.reject('STALE_OR_INELIGIBLE_APPROVAL',self.rt.approve,'task',task['payload_hash'])
        self.reject('APPROVAL_REQUIRED',self.rt.execute,'task',docs)
        self.rt.approve('task',newer['payload_hash'])
        self.assertEqual(self.rt.execute('task',docs)['state'],'DONE')

    def test_no_context_abstains(self):
        self.rt.create('task','zxqv9876')
        self.assertEqual(self.rt.prepare('task')['state'],'ABSTAINED')
        self.reject('TASK_NOT_EXECUTABLE',self.rt.execute,'task')

    def test_real_go_math_frame_and_decimal_precision(self):
        task=self.ready(query='calculate 0.10 + 0.20 USD')
        payload=json.loads(task['payload'])
        self.assertEqual(payload['computation']['total_minor_units'],30)
        self.assertEqual(payload['onion']['frame'],'math')
        self.rt.execute('task')

    def test_real_go_topology_frame_from_explicit_links(self):
        self.rt.import_document('alpha','Alpha','Project source [[beta]]')
        self.rt.import_document('beta','Beta','Completion evidence')
        task=self.ready(query='route from alpha to beta')
        self.assertEqual(json.loads(task['payload'])['computation']['path'],['alpha','beta'])
        self.rt.execute('task')

    def test_case_isolation_and_source_spelling(self):
        self.rt.import_document('note','CaseA','UniqueALPHA source','case-a')
        self.rt.import_document('note','CaseB','UniqueBETA source','case-b')
        self.rt.create('task-a','find UniqueALPHA','case-a')
        self.assertEqual(self.rt.prepare('task-a')['state'],'AWAITING_APPROVAL')
        self.rt.create('task-b','find UniqueALPHA','case-b')
        self.assertEqual(self.rt.prepare('task-b')['state'],'ABSTAINED')
        self.assertIn('UniqueALPHA',self.rt.task('task-a')['payload'])

    def test_local_feed_then_hydration(self):
        from feeds import local
        source=Path(self.tmp.name)/'notes';source.mkdir()
        (source/'meeting.md').write_text('Quarterly meeting agenda and timezone',encoding='utf8')
        (source/'.hidden.md').write_text('Do not import hidden files',encoding='utf8')
        result=local(self.rt,source,'meeting-case')
        self.assertEqual(result['captured'],1)
        self.rt.create('task','find meeting agenda','meeting-case')
        self.assertEqual(self.rt.prepare('task')['state'],'AWAITING_APPROVAL')

    def test_cloud_feed_destination_boundary(self):
        from feeds import public_url
        for url in ('http://example.com','https://127.0.0.1/','https://localhost/'):
            with self.assertRaises(ValueError):public_url(url)

    def test_stateless_worker_has_no_cross_call_context(self):
        from workers import call
        first=call('onion.parse',{'text':'find invoice policy'})
        second=call('onion.parse',{'text':'find meeting agenda'})
        self.assertNotIn('invoice',second['keywords'])
        self.assertEqual(first,call('onion.parse',{'text':'find invoice policy'}))

    def test_cpu_reranker_feedback_is_case_query_and_source_scoped(self):
        self.rt.create('task','find release policy')
        task=self.rt.prepare('task');before=json.loads(task['payload'])['ranking'][0]
        self.rt.feedback('task',before['id'],-1)
        self.rt.create('next','find release policy')
        after=json.loads(self.rt.prepare('next')['payload'])['ranking'][0]
        self.assertAlmostEqual(after['feedback_adjustment'],-0.25)
        self.rt.create('other-query','find release rollback')
        different=json.loads(self.rt.prepare('other-query')['payload'])['ranking'][0]
        self.assertEqual(different['feedback_adjustment'],0)

    def test_hydrate_no_network_and_explicit_frame(self):
        self.rt.create('task','Please summarize release policy')
        task=self.rt.prepare('task');payload=json.loads(task['payload'])
        self.assertEqual(payload['onion']['intent'],'brief')
        self.assertEqual(payload['onion']['frame'],'context')
        self.assertIn('Release review policy',payload['draft'])

    def test_capsule_topology_dictionary_and_projection(self):
        from capsules import capsule
        self.rt.import_document('alpha','ALPHA','ExactCase term [[beta]]','case-a')
        self.rt.import_document('beta','Beta','Related record','case-a')
        self.rt.define('case-a','ExactCase','An explicit local definition')
        value=capsule(self.rt,'case-a')
        self.assertEqual({s['id'] for s in value['sources']},{'alpha','beta'})
        self.assertTrue(any(w['spelling']=='ExactCase' for w in value['semantic_index']))
        self.assertTrue(any(e['relation']=='HAS_SCOPED_DEFINITION' for e in value['topology']['edges']))
        ids={n['id'] for n in value['topology']['nodes']}
        self.assertTrue(all(e['from'] in ids and e['to'] in ids for e in value['topology']['edges']))
        self.assertEqual(value['version'],capsule(self.rt,'case-a')['version'])

    def test_scoped_dictionary_routes_and_revision_revokes_approval(self):
        self.rt.import_document('release','Release checklist','Review release checklist','case-a')
        self.rt.define('case-a','launchgate','release checklist')
        self.rt.create('task','find launchgate','case-a')
        task=self.rt.prepare('task')
        self.assertEqual(task['state'],'AWAITING_APPROVAL')
        self.assertEqual(json.loads(task['payload'])['sources'][0]['id'],'release')
        self.rt.approve('task',task['payload_hash'])
        self.rt.define('case-a','launchgate','different meaning')
        self.reject('DEFINITION_CHANGED_REPREPARE_REQUIRED',self.rt.execute,'task')

    def test_cloud_spider_then_case_hydration(self):
        import io
        from unittest.mock import patch
        from email.message import Message
        from feeds import cloud
        class Response(io.BytesIO):
            def __init__(self,body,kind):
                super().__init__(body);self.headers=Message();self.headers['Content-Type']=kind
        class Opener:
            def open(self,request,timeout):
                if request.full_url.endswith('/robots.txt'):return Response(b'User-agent: *\nAllow: /','text/plain')
                return Response(b'<html><p>Release checklist and reviewer notes</p></html>','text/html')
        with patch('feeds.public_url',side_effect=lambda url,origin=None:url),patch('feeds.build_opener',return_value=Opener()):
            result=cloud(self.rt,'https://example.org/','cloud-case',1)
        self.assertEqual(result['captured'],1)
        self.rt.create('task','find release checklist','cloud-case')
        self.assertEqual(self.rt.prepare('task')['state'],'AWAITING_APPROVAL')

    def test_utf8_unicode_roundtrip_without_normalization(self):
        text='Résumé café — 東京 — مرحبا — 🧭 — e\u0301'
        docs=[{'id':'unicode-document','title':'Unicode reference','text':text}]
        self.rt.create('task','Unicode reference')
        task=self.rt.prepare('task',docs)
        self.rt.approve('task',task['payload_hash'])
        self.rt.execute('task',docs)
        self.rt.close();self.rt=Runtime(self.path)
        artifact=json.loads(self.rt.view()['artifacts'][0]['body'])
        self.assertEqual(artifact['draft'],'Unicode reference\n'+text)
        self.assertEqual(artifact['sources'][0]['hash'],digest(docs[0]))
        self.rt.verify()

    def test_untrusted_source_is_not_authority(self):
        self.rt.create('task','publish immediately')
        task=self.rt.prepare('task')
        self.assertIn('Ignore the approval',json.loads(task['payload'])['draft'])
        self.reject('APPROVAL_REQUIRED',self.rt.execute,'task')
        self.assertEqual(self.rt.view()['artifacts'],[])

    def test_cancellation_survives_restart(self):
        self.ready();self.rt.cancel('task');self.rt.close();self.rt=Runtime(self.path)
        self.reject('TASK_NOT_EXECUTABLE',self.rt.execute,'task')
        self.reject('TERMINAL_TASK',self.rt.prepare,'task')

    def test_duplicate_request_conflict_and_replay(self):
        self.ready();self.rt.create('task','release reviewer rollback')
        self.reject('IDEMPOTENCY_CONFLICT',self.rt.create,'task','different request')
        for _ in range(5):self.rt.execute('task')
        self.assertEqual(len(self.rt.view()['artifacts']),1)
        self.assertEqual(self.rt.verify()['events'],4)

    def test_receipt_tamper_detected(self):
        self.ready();self.rt.execute('task')
        self.rt.db.execute("UPDATE events SET data='{}' WHERE sequence=1")
        self.reject('RECEIPT_CHAIN_INVALID',self.rt.verify)

    def test_payload_and_tool_tamper_denied(self):
        self.ready();self.rt.db.execute("UPDATE tasks SET payload='{}' WHERE id='task'")
        self.reject('PAYLOAD_OR_POLICY_CHANGED',self.rt.execute,'task')
        self.assertEqual(self.rt.db.execute('SELECT count(*) FROM artifacts').fetchone()[0],0)

    def test_artifact_tamper_detected_on_replay(self):
        self.ready();self.rt.execute('task')
        self.rt.db.execute("UPDATE artifacts SET body='{}' WHERE task='task'")
        self.reject('ARTIFACT_INTEGRITY_FAILURE',self.rt.execute,'task')
        self.reject('ARTIFACT_INTEGRITY_FAILURE',self.rt.verify)

    def crash(self,point,expected):
        self.ready()
        process=subprocess.Popen([sys.executable,str(ROOT/'app.py'),'worker','--db',str(self.path),'--id','task','--cut',point],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        # Bounded reader: a broken worker cannot hang the evaluation.
        result=[]
        reader=threading.Thread(target=lambda:result.append(process.stdout.readline()),daemon=True);reader.start();reader.join(10)
        try:self.assertEqual(result,['FAULT_READY\n'])
        finally:
            process.kill();process.wait(timeout=10)
            process.stdout.close();process.stderr.close()
        self.rt.close();self.rt=Runtime(self.path)
        self.assertEqual(self.rt.task('task')['state'],expected)
        self.rt.verify()
        self.rt.execute('task');self.rt.execute('task')
        self.assertEqual(len(self.rt.view()['artifacts']),1)
        self.assertEqual(self.rt.verify()['events'],4)

    def test_process_kill_before_commit_rolls_back(self):
        self.crash('after_artifact_before_commit','AWAITING_APPROVAL')

    def test_process_kill_after_commit_replays_without_duplicate(self):
        self.crash('after_commit_before_ack','DONE')

    def test_concurrent_workers_commit_one_artifact(self):
        self.ready()
        workers=[subprocess.Popen([sys.executable,str(ROOT/'app.py'),'worker','--db',str(self.path),'--id','task'],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(6)]
        try:
            for worker in workers:
                out,err=worker.communicate(timeout=20)
                self.assertEqual(worker.returncode,0,err.decode())
            self.assertEqual(len(self.rt.view()['artifacts']),1)
            self.assertEqual(self.rt.verify()['events'],4)
        finally:
            for worker in workers:
                if worker.poll() is None:worker.kill();worker.wait()

    def test_invalid_inputs_and_duplicate_sources(self):
        self.reject('INVALID_TASK_ID',self.rt.create,'../task','release')
        self.reject('INVALID_QUERY',self.rt.create,'task','')
        self.rt.create('task','release')
        docs=self.rt.documents();docs.append(copy.deepcopy(docs[0]))
        self.reject('INVALID_CORPUS',self.rt.prepare,'task',docs)

    def test_http_origin_token_boundary_and_ui_action(self):
        server=serve(self.path)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        def post(data,origin,token='invalid'):
            req=Request(base+'/api/action',data=json.dumps(data).encode(),headers={'Origin':origin,'Authorization':'Bearer '+token,'Content-Type':'application/json'})
            with urlopen(req,timeout=5) as response:return json.load(response)
        try:
            with urlopen(base+'/api/session',timeout=5) as response:token=json.load(response)['token']
            for origin,credential in [(base,'invalid'),('https://example.org',token)]:
                with self.assertRaises(HTTPError) as error:post({'action':'create','id':'task','query':'release'},origin,credential)
                self.assertEqual(error.exception.code,403)
            self.assertEqual(post({'action':'create','id':'task','query':'release'},base,token)['state'],'NEW')
            task=post({'action':'prepare','id':'task'},base,token)
            post({'action':'approve','id':'task','payload_hash':task['payload_hash']},base,token)
            self.assertEqual(post({'action':'execute','id':'task'},base,token)['state'],'DONE')
        finally:server.shutdown();server.server_close();thread.join(5)
