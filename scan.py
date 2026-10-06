"""On-demand capability observation; no credential discovery or system changes."""
import hashlib
import platform
import shutil
import sqlite3
from workers import binary,call


def scan():
    items=[{'id':'local-python','status':'OBSERVED','version':platform.python_version(),'zone':'durable control'},
           {'id':'sqlite','status':'OBSERVED','version':sqlite3.sqlite_version,'zone':'persistent state'},
           {'id':'go-build-tool','status':'OBSERVED' if shutil.which('go') else 'NOT_FOUND','zone':'worker build'}]
    target=binary()
    if target.exists():
        try:
            result=call('onion.parse',{'text':'find capability evidence'})
            items.append({'id':'go-onion-worker','status':'OBSERVED_REQUEST_SUCCEEDED','binary_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'protocol':result['schema'],'zone':'language/math/topology'})
        except Exception:items.append({'id':'go-onion-worker','status':'REQUEST_FAILED'})
    else:items.append({'id':'go-onion-worker','status':'NOT_BUILT'})
    return {'schema':'ikea-scan/1','role':'ON_DEMAND_CAPABILITY_OBSERVATION_NOT_AUTHORITY','items':items,
        'cloud_llm':None,'wsl_runtime_acceptance':None,'computer_screen_capture':None,'qos':{'request_bytes':8192,'worker_input_bytes':65536,'worker_timeout_seconds':3,'cloud_pages_max':8,'cloud_page_bytes':262144,'background_polling':False}}
