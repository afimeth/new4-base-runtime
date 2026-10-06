"""Zookeeper's bounded process adapter for the Go language/math/topology worker."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading

ROOT=Path(__file__).resolve().parent
BUILD_LOCK=threading.Lock()
TOOLS=('onion.parse','math.sum','graph.route','search.rank')


def binary():return ROOT/'.state'/('tool-worker.exe' if os.name=='nt' else 'tool-worker')


def ensure_worker():
    with BUILD_LOCK:
        target=binary();target.parent.mkdir(exist_ok=True)
        files=[ROOT/'go.mod',ROOT/'cmd/worker/main.go']
        version=hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()
        stamp=Path(str(target)+'.source-hash')
        if not target.exists() or not stamp.exists() or stamp.read_text()!=version:
            subprocess.run(['go','build','-o',str(target),'./cmd/worker'],cwd=ROOT,check=True,timeout=120,capture_output=True)
            stamp.write_text(version,encoding='utf8')
        return target


def call(tool,value):
    if tool not in TOOLS:raise ValueError('TOOL_NOT_ALLOWED')
    request={'schema':'worker-request/1','id':hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'tool':tool,'input':value}
    raw=json.dumps(request,ensure_ascii=False).encode('utf8')
    if len(raw)>65536:raise ValueError('WORKER_INPUT_LIMIT')
    target=binary()
    if not target.exists():raise ValueError('WORKER_NOT_BUILT_RUN_SETUP')
    try:process=subprocess.run([str(target)],input=raw,capture_output=True,timeout=3)
    except subprocess.TimeoutExpired as exc:raise ValueError('WORKER_TIMEOUT') from exc
    except OSError as exc:raise ValueError('WORKER_START_FAILED') from exc
    if len(process.stdout)>131072:raise ValueError('WORKER_OUTPUT_LIMIT')
    try:response=json.loads(process.stdout.decode('utf8'))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise ValueError('WORKER_PROTOCOL_MISMATCH') from exc
    if response.get('id')!=request['id'] or response.get('schema')!='worker-response/1' or response.get('tool')!=tool or response.get('external_effects') is not False:raise ValueError('WORKER_PROTOCOL_MISMATCH')
    if process.returncode or response.get('error'):raise ValueError(response.get('error') or 'WORKER_FAILED')
    return response['result']
