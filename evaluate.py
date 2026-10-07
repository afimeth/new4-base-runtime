"""Emit fixture eval measurements bound to source bytes; fail on any scenario."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time
import unittest
from datetime import datetime, timezone
from runtime import ROOT, digest


def source_hashes():
    paths=['runtime.py','app.py','evaluate.py','tests/test_workflow.py','fixtures/documents.json','web/index.html','web/ui.js','web/style.css',
           'workers.py','feeds.py','capsules.py','project_map.py','context.py','scan.py','qos.py','go.mod','cmd/worker/main.go','cmd/worker/main_test.go',
           'scripts/project.py','scripts/check_public.py','contracts/dictionary.json','contracts/design.json','contracts/claims.json','contracts/hypotheses.json',
           'contracts/room.json','scripts/build_linux.py','scripts/go_evaluate.py','schemas/evaluation.schema.json','.github/workflows/evidence.yml']
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}


def evaluate(output):
    class Result(unittest.TestResult):
        def __init__(self):super().__init__();self.rows=[]
        def startTest(self,test):super().startTest(test);self.started=time.perf_counter_ns()
        def record(self,test,status,detail=None):
            self.rows.append({'id':test.id(),'status':status,'elapsed_ms':(time.perf_counter_ns()-self.started)/1e6,'detail':detail})
        def addSuccess(self,test):super().addSuccess(test);self.record(test,'PASS')
        def addFailure(self,test,err):super().addFailure(test,err);self.record(test,'FAIL',self._exc_info_to_string(err,test))
        def addError(self,test,err):super().addError(test,err);self.record(test,'ERROR',self._exc_info_to_string(err,test))
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=Result();suite.run(result)
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,stderr=subprocess.DEVNULL,text=True).strip()
    except subprocess.CalledProcessError:commit=None
    # This numerator counts fixture cases only, not production task success.
    report={'schema':'evaluation/1','timestamp':datetime.now(timezone.utc).isoformat(),
        'environment':{'os':platform.system(),'python':platform.python_version(),'sqlite':__import__('sqlite3').sqlite_version},
        'source_commit_at_run':commit,'source_hashes':source_hashes(),'scope':'SYNTHETIC_LOCAL_FIXTURES_REAL_SQLITE_REAL_SUBPROCESSES',
        'planner':'deterministic-extractive/1','model_calls':0,'provider_cost_usd':0,'semantic_accuracy':None,'human_usability':None,
        'independent_review':None,'cases':result.rows,'passed':sum(r['status']=='PASS' for r in result.rows),'total':result.testsRun,
        'status':'PASS' if result.wasSuccessful() else 'FAIL','process_kill':'OS_PROCESS_TERMINATION_NOT_POWER_FAILURE',
        'receipt_hash':None}
    report['receipt_hash']=digest({k:v for k,v in report.items() if k!='receipt_hash'})
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'status':report['status'],'passed':report['passed'],'total':report['total'],'output':str(output)}))
    return 0 if result.wasSuccessful() else 1
