#!/usr/bin/env python3
"""Non-destructive local checks. Never silently substitutes mocks for integration."""
import argparse,compileall,json,shutil,subprocess,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--report',type=Path);args=p.parse_args()
checks=[]
def record(name,status,detail=''):checks.append({'check':name,'status':status,'detail':detail})
def command(name,argv):
    proc=subprocess.run(argv,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(proc.stdout);record(name,'passed' if proc.returncode==0 else 'failed',proc.stdout[-4000:]);return proc.returncode==0
record('Python compilation','passed' if all(compileall.compile_dir(ROOT/name,quiet=1) for name in ('src','semaphore','tools','tests')) else 'failed')
try:
    files=[f for folder in ('ansible','semaphore','examples','.github','.gitea')
           for f in (ROOT/folder).rglob('*') if f.suffix in {'.yml','.yaml'}]
    for f in files:yaml.safe_load(f.read_text())
    record('YAML parsing','passed',f'{len(files)} files')
except Exception as exc:record('YAML parsing','failed',str(exc))
command('Bash syntax',['bash','-n','install.sh'])
if shutil.which('node'):command('Browser JavaScript syntax',['node','--check','web/app.js'])
else:record('Browser JavaScript syntax','not_run','node not installed')
command('Unit and contract tests',[sys.executable,'-m','pytest','-q','tests'])
record('Real Docker / Semaphore / Ansible integration','not_run','Must run the documented acceptance tests on a dedicated Ubuntu 24.04 systemd VM. Unit and browser tests are not substitutes.')
record('Live Nextcloud deployment, backup and separate-host restoration','not_run','No homelab was accessed or deployed by the development checks.')
report={'release':'0.1.0a1','checks':checks,'success':not any(x['status']=='failed' for x in checks)}
if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));sys.exit(0 if report['success'] else 1)
