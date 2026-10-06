"""Cross-build the same stateless Go worker for Linux/WSL; no system install."""
import hashlib
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'.state/tool-worker'
target.parent.mkdir(exist_ok=True)
environment={**os.environ,'GOOS':'linux','GOARCH':'amd64'}
subprocess.run(['go','build','-o',str(target),'./cmd/worker'],cwd=ROOT,env=environment,check=True,timeout=120)
version=hashlib.sha256(b''.join((ROOT/p).read_bytes() for p in ('go.mod','cmd/worker/main.go'))).hexdigest()
Path(str(target)+'.source-hash').write_text(version,encoding='utf8')
print('Linux amd64 worker built; runtime acceptance requires an actual Linux execution.')
