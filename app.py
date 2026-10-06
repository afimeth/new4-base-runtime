"""CLI and loopback HMI for the synthetic context-to-action workflow."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit,parse_qs
from runtime import Runtime, Rejected, ROOT, encoded
from workers import ensure_worker
from qos import TokenBucket


def serve(database, port=0):
    token=secrets.token_urlsafe(32)
    bucket=TokenBucket()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass  # Never log session credentials or request bodies.

        def host_ok(self):
            return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'

        def reply(self,code,data,kind='application/json'):
            raw=(encoded(data) if kind=='application/json' else data).encode()
            self.send_response(code)
            self.send_header('Content-Type',kind+'; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers();self.wfile.write(raw)

        def do_GET(self):
            if not self.host_ok():return self.reply(403,{'error':'HOST_REJECTED'})
            path=urlsplit(self.path).path
            if path in ('/','/ui.js','/style.css'):
                name={'/':'index.html','/ui.js':'ui.js','/style.css':'style.css'}[path]
                kind={'/':'text/html','/ui.js':'text/javascript','/style.css':'text/css'}[path]
                return self.reply(200,(ROOT/'web'/name).read_text(encoding='utf-8'),kind)
            if path=='/api/session':return self.reply(200,{'token':token,'identity_assurance':'LOCAL_SESSION_NOT_OWNER_IDENTITY'})
            if path=='/api/scan':
                from scan import scan
                return self.reply(200,scan())
            if path=='/api/state':
                runtime=Runtime(database)
                try:return self.reply(200,runtime.view())
                except Rejected as exc:return self.reply(409,{'error':str(exc)})
                finally:runtime.close()
            if path=='/api/capsule':
                runtime=Runtime(database)
                try:
                    from capsules import capsule
                    params=parse_qs(urlsplit(self.path).query)
                    if set(params)-{'case'} or any(len(v)!=1 for v in params.values()):raise ValueError('INVALID_QUERY')
                    return self.reply(200,capsule(runtime,params.get('case',['demo'])[0]))
                except ValueError as exc:return self.reply(422,{'error':str(exc)})
                finally:runtime.close()
            return self.reply(404,{'error':'NOT_FOUND'})

        def do_POST(self):
            if not self.host_ok():return self.reply(403,{'error':'HOST_REJECTED'})
            origin=f'http://127.0.0.1:{self.server.server_port}'
            if self.headers.get('Origin')!=origin or not secrets.compare_digest(self.headers.get('Authorization',''),f'Bearer {token}'):
                return self.reply(403,{'error':'LOCAL_SESSION_REQUIRED'})
            if not bucket.admit():return self.reply(429,{'error':'LOCAL_RATE_LIMIT','retry_after_seconds':1})
            if self.path!='/api/action':return self.reply(404,{'error':'NOT_FOUND'})
            try:
                self.connection.settimeout(5)
                length=int(self.headers.get('Content-Length','0'))
                if not 1<=length<=8192:raise Rejected('BODY_LIMIT')
                if self.headers.get('Content-Type')!='application/json':raise Rejected('JSON_REQUIRED')
                value=json.loads(self.rfile.read(length))
                if not isinstance(value,dict) or set(value)-{'action','id','query','payload_hash','case_id','title','text','source','rating','term','meaning'}:raise Rejected('INVALID_REQUEST')
                action=value.get('action');identifier=value.get('id')
                if not isinstance(identifier,str):raise Rejected('INVALID_TASK_ID')
                runtime=Runtime(database)
                try:
                    if action=='create':result=runtime.create(identifier,value.get('query'),value.get('case_id','demo'))
                    elif action=='prepare':result=runtime.prepare(identifier)
                    elif action=='approve':result=runtime.approve(identifier,value.get('payload_hash'))
                    elif action=='execute':result=runtime.execute(identifier)
                    elif action=='cancel':result=runtime.cancel(identifier)
                    elif action=='import':
                        from feeds import safe_text
                        result=runtime.import_document(identifier,value.get('title'),safe_text(value.get('text','')),value.get('case_id','demo'))
                    elif action=='feedback':result=runtime.feedback(identifier,value.get('source'),value.get('rating'))
                    elif action=='define':result=runtime.define(value.get('case_id','demo'),value.get('term'),value.get('meaning'))
                    elif action=='export':
                        from capsules import export
                        result=export(runtime,value.get('case_id','demo'))
                    else:raise Rejected('UNKNOWN_ACTION')
                    self.reply(200,result)
                finally:runtime.close()
            except (Rejected,ValueError,TypeError,KeyError,TimeoutError) as exc:
                self.reply(422,{'error':str(exc) if isinstance(exc,Rejected) else 'INVALID_REQUEST'})

    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    return server


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('demo','serve','evaluate','worker','verify','setup','feed-local','feed-cloud','feed-alexandria','capsule','define','scan','context','consolidate','map-code'))
    parser.add_argument('--db',default=str(ROOT/'.state/runtime.sqlite'))
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--id',default='release-demo')
    parser.add_argument('--cut',choices=('after_artifact_before_commit','after_commit_before_ack'))
    parser.add_argument('--output',default=str(ROOT/'evidence/local-eval.json'))
    parser.add_argument('--case',default='demo')
    parser.add_argument('--folder')
    parser.add_argument('--url')
    parser.add_argument('--term')
    parser.add_argument('--meaning')
    parser.add_argument('--query')
    args=parser.parse_args()
    Path(args.db).parent.mkdir(parents=True,exist_ok=True)
    if args.action=='evaluate':
        from evaluate import evaluate
        return evaluate(Path(args.output))
    if args.action=='setup':
        ensure_worker();print(encoded({'worker':'go-onion','status':'BUILT_LOCAL'}));return 0
    if args.action=='scan':
        from scan import scan
        print(encoded(scan()));return 0
    if args.action=='serve':
        ensure_worker()
        server=serve(args.db,args.port)
        print(encoded({'url':f'http://127.0.0.1:{server.server_port}','mode':'LOCAL_SYNTHETIC_ONLY'}),flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
        return 0
    runtime=Runtime(args.db)
    try:
        if args.action=='demo':
            ensure_worker()
            runtime.create(args.id,'release reviewer rollback')
            if runtime.task(args.id)['state']!='DONE':
                runtime.prepare(args.id)
                runtime.approve(args.id,runtime.task(args.id)['payload_hash'],'demo-script')
                runtime.execute(args.id)
            print(encoded(runtime.view()))
        elif args.action=='verify':print(encoded(runtime.verify()))
        elif args.action=='feed-local':
            from feeds import local
            print(encoded(local(runtime,args.folder,args.case)))
        elif args.action=='feed-cloud':
            from feeds import cloud
            print(encoded(cloud(runtime,args.url,args.case)))
        elif args.action=='feed-alexandria':
            from feeds import alexandria
            print(encoded(alexandria(runtime,args.url,args.query,args.case)))
        elif args.action=='capsule':
            from capsules import export
            print(encoded(export(runtime,args.case)))
        elif args.action=='define':print(encoded(runtime.define(args.case,args.term,args.meaning)))
        elif args.action=='context':
            from context import assemble
            ensure_worker();print(encoded(assemble(runtime,args.case,args.query)))
        elif args.action=='consolidate':
            from context import consolidate
            print(encoded(consolidate(runtime,args.case)))
        elif args.action=='map-code':
            from context import code_map
            print(encoded(code_map(args.folder)))
        else:
            def fault(point):
                if point==args.cut:
                    print('FAULT_READY',flush=True)
                    time.sleep(120)  # Test parent terminates this OS process here.
            runtime.execute(args.id,fault=fault if args.cut else None)
            print('WORKER_DONE',flush=True)
    except Rejected as exc:
        print(encoded({'error':str(exc)}));return 2
    finally:runtime.close()
    return 0


if __name__=='__main__':raise SystemExit(main())
