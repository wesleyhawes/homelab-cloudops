#!/usr/bin/env python3
"""Browser acceptance of the UI against an explicitly simulated local API."""
import json,os,threading,time
from pathlib import Path
from playwright.sync_api import sync_playwright
from preview import DemoServer,marker
ROOT=Path(__file__).resolve().parents[1]
REPORT_DIR=Path(os.environ.get('CLOUDOPS_VALIDATION_DIR',str(ROOT/'validation')))
server=DemoServer(('127.0.0.1',0));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}';checks=[];screens=REPORT_DIR/'screenshots';screens.mkdir(parents=True,exist_ok=True)
def passed(name):checks.append({'check':name,'status':'passed'})
try:
 with sync_playwright() as p:
    executable=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium')
    browser=p.chromium.launch(executable_path=executable if Path(executable).exists() else None,headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1050},device_scale_factor=1)
    page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base+'/cloudops/');page.get_by_role('link',name='Open secure sign-in').wait_for()
    assert page.locator('[data-operation="backup"]').is_disabled();passed('Signed-out operations are disabled')
    page.get_by_role('link',name='Open secure sign-in').click();page.get_by_role('link',name='Enter simulated owner session').click()
    page.locator('#health').filter(has_text='Checks passed').wait_for();assert page.locator('#demo-banner').is_visible();passed('Native-session handoff and simulated status rendering')
    page.screenshot(path=str(screens/'desktop-preview.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth');passed('Desktop has no horizontal overflow')
    page.locator('[data-operation="backup"]').click();assert page.locator('#confirm-submit').is_disabled();page.get_by_role('button',name='Cancel',exact=True).click();assert len(server.submissions)==0;passed('Cancellation and unchecked approval do not submit')
    page.locator('[data-operation="backup"]').click();page.locator('#approval').check();page.locator('#confirm-submit').click()
    page.wait_for_function("document.querySelector('#log-status').textContent === 'running'")
    assert len(server.submissions)==1 and json.loads(server.submissions[0]['environment'])=={'cloudops_confirmation':'PROCEED'};passed('Confirmed action submits one native task with approval variable')
    selected=page.evaluate("localStorage.getItem('cloudops-selected')");page.reload();page.wait_for_function("document.querySelector('#log-status').textContent === 'running'")
    assert page.evaluate("localStorage.getItem('cloudops-selected')")==selected;passed('Page reload reconnects to the selected simulated running task')
    server.outputs[int(selected)].append({'output':'<img src=x onerror="window.cloudopsInjected=true">'})
    page.reload();page.wait_for_function("document.querySelector('#log-output').textContent.includes('<img')")
    assert page.evaluate('window.cloudopsInjected') is None and page.locator('img').count()==0;passed('Task output is rendered as text, not executable HTML')
    phone=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
    phone.add_cookies(context.cookies());mobile=phone.new_page();mobile.goto(base+'/cloudops/');mobile.locator('#health').filter(has_text='Checks passed').wait_for()
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth');passed('390px mobile layout has no horizontal overflow')
    mobile.screenshot(path=str(screens/'mobile-preview.png'),full_page=True)
    mobile.get_by_role('link',name='Guide',exact=True).click();mobile.get_by_role('heading',name='From installation to recovery.').wait_for();assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth');passed('Mobile guide navigation works without overflow')
    assert not errors,errors;passed('No unhandled browser JavaScript errors during the tested flows')
    browser.close()
finally:server.close()
report={'scope':'Chromium against a simulated local Semaphore API; not a real deployment, authentication audit, or systemd disconnect test.','checks':checks}
(REPORT_DIR/'browser-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
