"""Owner-only manager snapshot. Plaintext by design; encrypt before off-host storage."""
from __future__ import annotations
import json,os,re,sqlite3,tarfile,tempfile,uuid
from pathlib import Path
from . import paths
from .errors import CloudOpsError
from .jobs import JobStore
from .util import require_root,run


def snapshot(destination: Path) -> dict:
    require_root()
    if not destination.is_absolute() or destination.exists():
        raise CloudOpsError("Use a new absolute output path; manager snapshots never overwrite an existing file.")
    resolved=destination.resolve()
    if resolved.is_relative_to(Path('/etc/cloudops')) or resolved.is_relative_to(paths.STATE.resolve()):
        raise CloudOpsError("Place the snapshot outside the configuration and operation-state directories.")
    store=JobStore(paths.STATE)
    if any(j['status'] in {'queued','running'} for j in store.list(limit=10000)):
        raise CloudOpsError("Wait for active host operations before taking a manager snapshot.")
    compose=['docker','compose','-f','/etc/cloudops/manager.compose.yaml']
    ids={}
    for service in ('semaphore','gateway'):
        cid=run(compose+['ps','-q',service]).stdout.strip()
        if not re.fullmatch(r'[a-f0-9]{12,64}',cid):
            raise CloudOpsError("Both manager services must be running for this snapshot workflow.")
        ids[service]=cid
    destination.parent.mkdir(parents=True,exist_ok=True)
    token=uuid.uuid4().hex
    remote=f'/tmp/cloudops-manager-snapshot-{token}.sqlite'
    script='import sqlite3,sys; src=sqlite3.connect("file:"+sys.argv[1]+"?mode=ro",uri=True); dst=sqlite3.connect(sys.argv[2]); src.backup(dst); dst.close(); src.close()'
    old=os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix='cloudops-manager-',dir=paths.STATE) as temp:
            work=Path(temp)
            try:
                run(['docker','exec',ids['semaphore'],'python3','-c',script,'/var/lib/semaphore/cloudops.sqlite',remote],timeout=120)
                run(['docker','cp',ids['semaphore']+':'+remote,str(work/'semaphore.sqlite')],timeout=120)
            finally:
                run(['docker','exec',ids['semaphore'],'python3','-c','import os,sys; os.unlink(sys.argv[1])',remote],check=False)
            for service,source,target in [('semaphore','/etc/semaphore','semaphore-config'),('gateway','/data/caddy','caddy-state')]:
                run(['docker','cp',ids[service]+':'+source,str(work/target)],timeout=120)
            with sqlite3.connect('file:'+str(store.db)+'?mode=ro',uri=True) as source,sqlite3.connect(work/'jobs.sqlite') as target:
                source.backup(target)
            info={'scope':'Manager only; no application data/Borg repository','encrypted':False,'contains_secrets':True,
                  'warning':'Encrypt and independently protect this root-only archive before moving it off-host.'}
            (work/'SNAPSHOT.json').write_text(json.dumps(info,indent=2)+'\n')
            # Exclusive creation; avoid truncating a file created between preflight and write.
            with destination.open('xb') as output:
                with tarfile.open(fileobj=output,mode='w:gz') as tar:
                    tar.add(work,arcname='manager-snapshot')
                    tar.add('/etc/cloudops',arcname='etc-cloudops')
                    for filename in ('deployment.json','last-backup.json','last-integrity.json','last-restore-test.json','probe-manifest.json','management-images.json','python-installed.txt'):
                        source=paths.STATE/filename
                        if source.exists():tar.add(source,arcname='host-state/'+filename,recursive=False)
            destination.chmod(0o600)
            return info|{'path':str(destination)}
    except (OSError,sqlite3.Error,tarfile.TarError) as exc:
        raise CloudOpsError("Manager snapshot failed. Inspect the destination; a partial archive must not be used as a backup.") from exc
    finally:os.umask(old)
