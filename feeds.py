"""Bounded, explicit local/public-cloud dual feeding; no background polling."""
import hashlib
from html.parser import HTMLParser
import ipaddress
from pathlib import Path
import re
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

AGENT='OnionFeed/1.0'
SENSITIVE=re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16})\b|(?i:password|api_key|access_token)\s*[:=]\s*[\x22\x27][^\x22\x27\s]{8,}[\x22\x27]')


def safe_text(value):
    if SENSITIVE.search(value):raise ValueError('SENSITIVE_CONTENT_HOLD')
    return value


def local(runtime,folder,case_id='demo',max_files=16):
    root=Path(folder).resolve(strict=True)
    if not root.is_dir():raise ValueError('LOCAL_DIRECTORY_REQUIRED')
    if not 1<=max_files<=64:raise ValueError('FILE_COUNT_LIMIT')
    paths=sorted(p for p in root.rglob('*') if p.suffix.lower() in ('.txt','.md'))[:max_files]
    result=[]
    for path in paths:
        relative=path.relative_to(root)
        if any(part.startswith('.') or part.lower() in ('node_modules','secrets','credentials') for part in relative.parts) or re.search('secret|credential|password|token|private.?key',path.name,re.I):continue
        if path.is_symlink() or not path.resolve().is_relative_to(root) or path.stat().st_size>32768:continue
        try:text=safe_text(path.read_text(encoding='utf8'))
        except (UnicodeDecodeError,ValueError):continue
        if not 1<=len(text)<=8000:continue
        identifier='local-'+hashlib.sha256(str(relative).encode()).hexdigest()[:20]
        result.append(runtime.import_document(identifier,path.stem,text,case_id,{'kind':'LOCAL_TEXT','relative_path':str(relative),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))
    return {'schema':'feed-result/1','kind':'LOCAL','captured':len(result),'items':result,'scheduled':False,'coverage':'Selected UTF-8 text files only; sensitive, binary, oversized and symlink sources are excluded'}


def public_url(value,origin=None):
    parts=urlsplit(value)
    if parts.scheme!='https' or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.port not in (None,443):raise ValueError('PUBLIC_HTTPS_URL_REQUIRED')
    normalized=urlunsplit(('https',parts.hostname,parts.path or '/','',''))
    if origin and urlsplit(normalized).netloc!=urlsplit(origin).netloc:raise ValueError('CROSS_ORIGIN_NOT_ALLOWED')
    addresses=socket.getaddrinfo(parts.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('NON_PUBLIC_DESTINATION')
    return normalized


class Page(HTMLParser):
    def __init__(self):super().__init__();self.text=[];self.links=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','form'):self.skip+=1
        if tag=='a':
            href=dict(attrs).get('href')
            if href:self.links.append(href)
    def handle_endtag(self,tag):
        if tag in ('script','style','form') and self.skip:self.skip-=1
    def handle_data(self,value):
        if not self.skip:self.text.append(value)


def cloud(runtime,seed,case_id='demo',max_pages=3):
    if not 1<=max_pages<=8:raise ValueError('PAGE_COUNT_LIMIT')
    seed=public_url(seed)
    class Redirect(HTTPRedirectHandler):
        def redirect_request(self,request,fp,code,msg,headers,newurl):
            return super().redirect_request(request,fp,code,msg,headers,public_url(newurl,seed))
    opener=build_opener(Redirect())
    def fetch(url):
        public_url(url,seed)
        with opener.open(Request(url,headers={'User-Agent':AGENT}),timeout=10) as response:
            raw=response.read(262145)
            if len(raw)>262144:raise ValueError('PAGE_SIZE_LIMIT')
            return raw,response.headers.get_content_type()
    robot=RobotFileParser();parts=urlsplit(seed)
    try:rules,_=fetch('https://'+parts.netloc+'/robots.txt');robot.parse(rules.decode('utf8','replace').splitlines())
    except Exception as exc:raise ValueError('ROBOTS_UNAVAILABLE_HOLD') from exc
    queue=[seed];seen=set();items=[];gaps=[]
    while queue and len(seen)<max_pages:
        url=queue.pop(0)
        if url in seen:continue
        seen.add(url)
        if not robot.can_fetch(AGENT,url):gaps.append({'url':url,'status':'ROBOTS_DISALLOWED'});continue
        try:
            raw,kind=fetch(url)
            if kind not in ('text/html','text/plain'):raise ValueError('CONTENT_TYPE_HOLD')
            text=raw.decode('utf8',errors='strict');page=Page()
            if kind=='text/html':page.feed(text);text=' '.join(page.text)
            text=safe_text(' '.join(text.split()[:120]))
            if not text:raise ValueError('EMPTY_CONTENT')
            identifier='cloud-'+hashlib.sha256(url.encode()).hexdigest()[:20]
            items.append(runtime.import_document(identifier,parts.netloc+urlsplit(url).path,text,case_id,{'kind':'PUBLIC_CLOUD_EXCERPT','url':url,'response_sha256':hashlib.sha256(raw).hexdigest(),'word_budget':120}))
            for href in page.links[:32]:
                try:target=public_url(urljoin(url,href),seed)
                except (ValueError,OSError):continue
                if target not in seen and target not in queue:queue.append(target)
        except Exception:gaps.append({'url':url,'status':'SOURCE_ACCESS_HOLD'})
    return {'schema':'feed-result/1','kind':'PUBLIC_CLOUD','captured':len(items),'attempted':len(seen),'items':items,'gaps':gaps,'scheduled':False,'coverage':'Public same-origin excerpts only; no signed-in pages or private GitHub access'}


def alexandria(runtime,base,query,case_id='demo'):
    import json
    from urllib.parse import urlencode
    parts=urlsplit(base)
    if parts.scheme!='http' or parts.hostname!='127.0.0.1' or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ('','/') or not parts.port:raise ValueError('LOCAL_ALEXANDRIA_ORIGIN_REQUIRED')
    if not isinstance(query,str) or not 1<=len(query)<=2000:raise ValueError('INVALID_QUERY')
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):raise ValueError('LOCAL_REDIRECT_REJECTED')
    opener=build_opener(NoRedirect())
    url=base.rstrip('/')+'/api/fastwikitaxi?'+urlencode({'q':safe_text(query)})
    with opener.open(Request(url,headers={'Accept':'application/json'}),timeout=10) as response:
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('CAPSULE_RESPONSE_LIMIT')
        data=json.loads(raw.decode('utf8'))
    items=[]
    for entry in data.get('context',[])[:8]:
        identifier='alexandria-'+hashlib.sha256(entry['id'].encode()).hexdigest()[:20]
        text=safe_text(entry.get('excerpt') or entry.get('label') or '')[:8000]
        if not text:continue
        items.append(runtime.import_document(identifier,entry.get('label',entry['id'])[:160],text,case_id,{'kind':'LOCAL_ALEXANDRIA_BOUNDED_CONTEXT','original_id':entry['id'],'source_generation':data.get('source_generation'),'sources':entry.get('sources',[]),'captured_hash':entry.get('hash'),'semantic_confidence':data.get('semantic_confidence')}))
    return {'schema':'feed-result/1','kind':'LOCAL_ALEXANDRIA','captured':len(items),'items':items,'source_generation':data.get('source_generation'),'semantic_confidence':None,'coverage':'Up to eight returned bounded context entries, not full corpus hydration','external_publication':False}
