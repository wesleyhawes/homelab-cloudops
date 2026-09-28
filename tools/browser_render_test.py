#!/usr/bin/env python3
"""Render/test the UI with an IN-MEMORY API: no browser network-policy changes."""
import json,os,re
from pathlib import Path
from playwright.sync_api import sync_playwright
from preview import DemoServer
ROOT=Path(__file__).resolve().parents[1]
# Construct data fixtures; the HTTP server is not started or contacted.
fixture=DemoServer(('127.0.0.1',0))
data={'authenticated':True,'submissions':[], 'tasks':fixture.tasks,'outputs':fixture.outputs,
      'config':{'demo':True,'instance_id':'My personal cloud','provider':'nextcloud_aio','mode':'primary','project_id':1,
                'operations':fixture.operations,'cloud_url':'https://cloud.example.com','aio_url':'https://192.168.10.50:8080'}}
fixture.server_close()
data=json.loads(json.dumps(data))
html=(ROOT/'web/index.html').read_text();html=re.sub(r'<script[^>]*src="app.js"[^>]*></script>','',html);html=re.sub(r'<link[^>]*href="style.css"[^>]*>','',html)
css=(ROOT/'web/style.css').read_text();js=(ROOT/'web/app.js').read_text()
checks=[];screens=ROOT/'validation/screenshots';screens.mkdir(parents=True,exist_ok=True)
def passed(name):checks.append({'check':name,'status':'passed'})

MOCK=r"""(fixture)=>{
 window.fixture=fixture; window.testIntervals=[];
 window.setInterval=(fn)=>{window.testIntervals.push(fn);return window.testIntervals.length;};
 const storage={};Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>storage[k]||null,setItem:(k,v)=>storage[k]=String(v)}});
 window.fetch=async(url,options={})=>{
   const path=String(url);let value,status=200;
   if(path==='config.json'){value=fixture.config;}
   else if(!fixture.authenticated){status=401;value={};}
   else if(path==='/api/user/'){value={name:'Preview Owner',username:'admin'};}
   else if(path==='/api/project/1/tasks/last'){value=fixture.tasks;}
   else if(path.endsWith('/output')){value=fixture.outputs[path.split('/').at(-2)]||[];}
   else if(path==='/api/project/1/tasks'&&options.method==='POST'){
      const body=JSON.parse(options.body);fixture.submissions.push(body);
      value={id:104,template_id:body.template_id,created:new Date().toISOString(),status:'running'};
      fixture.tasks.unshift(value);fixture.outputs['104']=[{output:'SIMULATION ONLY: running-task fixture; no host operation was started.'}];
   }else{status=404;value={};}
   return new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
 };
}"""
try:
 with sync_playwright() as p:
    path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium')
    browser=p.chromium.launch(executable_path=path if Path(path).exists() else None,headless=True,args=['--no-sandbox'])
    def load(viewport,fixture_data):
        page=browser.new_page(viewport=viewport);page.set_content(html);page.add_style_tag(content=css);page.evaluate(MOCK,fixture_data);page.add_script_tag(content='(()=>{'+js+'})();');return page
    signedout=load({'width':390,'height':844},data|{'authenticated':False})
    signedout.get_by_role('link',name='Open secure sign-in').wait_for();assert signedout.locator('[data-operation="backup"]').is_disabled();passed('Signed-out state disables operation buttons')
    page=load({'width':1440,'height':1050},data);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.locator('#health').filter(has_text='Checks passed').wait_for();assert page.locator('#demo-banner').is_visible();passed('Status cards and simulation disclosure render from supplied API fixtures')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth');passed('1440px desktop layout has no horizontal overflow')
    page.screenshot(path=str(screens/'desktop-preview.png'),full_page=True)
    page.locator('[data-operation="backup"]').click();assert page.locator('#confirm-submit').is_disabled();page.get_by_role('button',name='Cancel',exact=True).click();assert page.evaluate('fixture.submissions.length')==0;passed('Unchecked approval and cancellation do not submit')
    page.locator('[data-operation="backup"]').click();page.locator('#approval').check();page.locator('#confirm-submit').click();page.wait_for_function("document.querySelector('#log-status').textContent === 'running'")
    sent=page.evaluate('fixture.submissions');assert len(sent)==1 and json.loads(sent[0]['environment'])=={'cloudops_confirmation':'PROCEED'};passed('One approved action generates one task request with the required confirmation')
    assert page.evaluate("localStorage.getItem('cloudops-selected')")=='104';passed('Selected task ID is saved through the browser storage interface (mocked storage)')
    page.evaluate("""fixture.outputs['104'].push({output:'<img src=x onerror="window.cloudopsInjected=true">'}); testIntervals.forEach(f=>f());""")
    page.wait_for_function("document.querySelector('#log-output').textContent.includes('<img')")
    assert page.evaluate('window.cloudopsInjected') is None and page.locator('img').count()==0;passed('Execution output is text, not interpreted HTML')
    mobile=load({'width':390,'height':844},data);mobile.locator('#health').filter(has_text='Checks passed').wait_for()
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth');passed('390px mobile layout has no horizontal overflow')
    mobile.screenshot(path=str(screens/'mobile-preview.png'),full_page=True)
    # Render the guide independently instead of navigating a blocked browser origin.
    guide=(ROOT/'web/guide.html').read_text();guide=re.sub(r'<link[^>]*href="style.css"[^>]*>','',guide)
    mobile.set_content(guide);mobile.add_style_tag(content=css)
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth');passed('Mobile guide renders without horizontal overflow')
    assert not errors,errors;passed('No unhandled JavaScript errors during the observed action/output flows')
    browser.close()
finally:
    report={'scope':'Chromium rendering and UI actions with an in-memory mocked API/storage. No browser network policies were changed. This does not validate live HTTP, native authentication/cookies, real localStorage persistence, reload reconnection, SSH, Ansible, Docker or systemd execution.',
            'checks':checks,'not_run':['Network-backed browser_smoke.py was blocked by the environment browser URL policy; run it on the development laptop/test VM.','Real phone browser tests and live native Semaphore integration.']}
    (ROOT/'validation/browser-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
