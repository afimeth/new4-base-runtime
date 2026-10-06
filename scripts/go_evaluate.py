"""Record actual Go test outcomes; no synthesized test results."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
process=subprocess.run(['go','test','-count=1','-json','./...'],cwd=ROOT,capture_output=True,text=True,timeout=120)
cases=[]
for line in process.stdout.splitlines():
    row=json.loads(line)
    if row.get('Test') and row.get('Action') in ('pass','fail','skip'):
        cases.append({'id':row['Package']+'.'+row['Test'],'status':row['Action'].upper(),'elapsed_seconds':row.get('Elapsed')})
report={'schema':'go-evaluation/1','timestamp':datetime.now(timezone.utc).isoformat(),'go_version':subprocess.check_output(['go','version'],text=True).strip(),'status':'PASS' if process.returncode==0 and cases and all(c['status']=='PASS' for c in cases) else 'FAIL','cases':cases,'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('go.mod','cmd/worker/main.go','cmd/worker/main_test.go')},'scope':'Go parser, ranker, math, topology and tool allowlist fixture tests'}
output=Path(sys.argv[1] if len(sys.argv)>1 else ROOT/'evidence/go-eval.json')
output.parent.mkdir(exist_ok=True,parents=True);output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps({'status':report['status'],'cases':len(cases)}));raise SystemExit(0 if report['status']=='PASS' else 1)
