#!/usr/bin/env python3
"""Local UI preview ONLY. Simulated API, no cloud deployment or authentication service."""
from __future__ import annotations
import base64,json,threading,time
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cloudops.semaphore_api import ACTIONS
ROOT=Path(__file__).resolve().parents[1]
def iso(minutes=0):return (datetime.now(timezone.utc)-timedelta(minutes=minutes)).isoformat()
def marker(data):return 'CLOUDOPS_RESULT_B64='+base64.b64encode(json.dumps(data).encode()).decode()

class DemoServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address=('127.0.0.1',8765)):
        super().__init__(address,Handler);self.lock=threading.Lock();self.submissions=[];self.nextid=104
        self.operations={op:{'id':i+1,'title':desc[0],'confirmation':desc[1],'description':desc[2]} for i,(op,desc) in enumerate(ACTIONS.items())}
        self.tasks=[{'id':103,'template_id':self.operations['check']['id'],'status':'success','created':iso(1)},
                    {'id':102,'template_id':self.operations['backup']['id'],'status':'success','created':iso(68)},
                    {'id':101,'template_id':self.operations['deploy']['id'],'status':'success','created':iso(120)}]
        summary={'job_id':'a'*32,'status':'success','checked_at':iso(1),'application_verified':True,'version':'preview',
                 'data_free_bytes':384*1024**3,'data_mount_verified':True,'last_backup':{'backup_verified':True,'finished_at':iso(65)},'last_restore_test':None}
        self.outputs={103:[{'output':'Preview fixture: Check required storage mount and application state.'},{'output':marker(summary)}],
                      102:[{'output':'Preview fixture: fresh Borg archive evidence verified.'},{'output':marker({'job_id':'b'*32,'status':'success','backup_verified':True,'restore_verified':False})}],
                      101:[{'output':'Preview fixture: mastercontainer started; native setup handoff.'},{'output':marker({'job_id':'c'*32,'status':'success','onboarding_required':True})}]}
    def close(self):self.shutdown();self.server_close()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,body=b'',content='application/json',headers=None):
        if isinstance(body,(dict,list)):body=json.dumps(body).encode()
        if isinstance(body,str):body=body.encode()
        self.send_response(status);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        for k,v in (headers or {}).items():self.send_header(k,v)
        self.end_headers();self.wfile.write(body)
    def authenticated(self):return 'cloudops_demo=1' in self.headers.get('Cookie','')
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/demo-login':return self.send(302,b'',headers={'Set-Cookie':'cloudops_demo=1; Path=/; HttpOnly; SameSite=Strict','Location':'/cloudops/'})
        if path=='/':return self.send(200,'<!doctype html><title>Simulation sign-in</title><h1>Local preview only</h1><p>This is not Semaphore and does not accept real credentials.</p><a href="/demo-login">Enter simulated owner session</a>','text/html')
        if path.startswith('/api/'):
            if not self.authenticated():return self.send(401,{'error':'simulation requires demo session'})
            if path=='/api/user/':return self.send(200,{'id':1,'name':'Preview Owner','username':'admin'})
            if path=='/api/project/1/tasks/last':return self.send(200,self.server.tasks)
            if path.startswith('/api/project/1/tasks/') and path.endswith('/output'):
                try:taskid=int(path.split('/')[-2]);return self.send(200,self.server.outputs.get(taskid,[]))
                except ValueError:return self.send(400,{})
            return self.send(404,{})
        if path=='/cloudops/config.json':return self.send(200,{'schema_version':1,'demo':True,'instance_id':'My personal cloud','provider':'nextcloud_aio','mode':'primary','project_id':1,'operations':self.server.operations,'cloud_url':'https://cloud.example.com','aio_url':'https://192.168.10.50:8080','release':'0.1.0a1'})
        names={'/cloudops/':('index.html','text/html'),'/cloudops/style.css':('style.css','text/css'),'/cloudops/app.js':('app.js','application/javascript'),'/cloudops/guide.html':('guide.html','text/html')}
        if path in names:
            filename,mime=names[path];return self.send(200,(ROOT/'web'/filename).read_bytes(),mime)
        return self.send(404,{'error':'Not found'})
    def do_POST(self):
        if not self.authenticated():return self.send(401,{})
        if self.path!='/api/project/1/tasks':return self.send(404,{})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>10000:return self.send(413,{})
            body=json.loads(self.rfile.read(length))
        except (ValueError,TypeError):return self.send(400,{})
        with self.server.lock:
            self.server.submissions.append(body);taskid=self.server.nextid;self.server.nextid+=1
            task={'id':taskid,'template_id':body['template_id'],'created':iso(),'status':'running'}
            self.server.tasks.insert(0,task)
            self.server.outputs[taskid]=[{'output':'SIMULATION ONLY: operation queued; the preview never contacts a cloud server.'}]
        return self.send(201,task)

if __name__=='__main__':
    server=DemoServer();print('SIMULATED UI ONLY: http://127.0.0.1:8765/cloudops/\nNo Docker, SSH, cloud or real credentials are used.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
