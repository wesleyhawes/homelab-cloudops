"""A systemd service process executes a fixed, local Ansible playbook."""
from __future__ import annotations
import fcntl
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from . import paths
from .config import Config
from .errors import CloudOpsError
from .jobs import JobStore
from .providers import provider_spec
from .util import require_root


def main(job_id: str) -> int:
    require_root()
    os.umask(0o077)
    store = JobStore(paths.STATE)
    job = store.get(job_id)
    if job["status"] != "queued":
        raise CloudOpsError("This job was already started; automatic replay is forbidden.")
    config = Config.load(paths.CONFIG)
    spec = provider_spec(config.provider, job["operation"])
    directory = store.directory(job_id)
    logpath = directory / "output.log"
    resultpath = directory / "result.json"
    with open(paths.STATE / "operation.lock", "a") as lock:
        # Advisory read-only checks may run while maintenance is active. Mutations serialize.
        if job["mutating"]:
            fcntl.flock(lock, fcntl.LOCK_EX)
        store.update(job_id, "running")
        env = {"PATH": f"{paths.VENV}/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "LANG": "C.UTF-8",
               "ANSIBLE_CONFIG": str(paths.RELEASE / "ansible/ansible.cfg"), "ANSIBLE_NOCOLOR": "1",
               "CLOUDOPS_RESULT_FILE": str(resultpath)}
        argv = [str(paths.VENV / "bin/ansible-playbook"), "-i", "localhost,", "-c", "local",
                str(paths.RELEASE / "ansible/playbooks/operation.yml"), "--extra-vars",
                json.dumps({"cloudops_role": spec.role, "cloudops_operation": job["operation"], "ansible_python_interpreter": str(paths.VENV / "bin/python")})]
        try:
            with logpath.open("w") as log:
                process = subprocess.Popen(argv, cwd=paths.RELEASE / "ansible", env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = process.wait(timeout=config.job_timeout_seconds + 1800)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    raise CloudOpsError("Observation timed out. Native AIO work may still be running; inspect before acknowledging.")
            result = json.loads(resultpath.read_text()) if resultpath.exists() else {}
            if code != 0 or not result:
                state = "attention" if job["mutating"] else "failed"
                store.update(job_id, state, result or {"error": "Ansible did not complete. Inspect this task's output and AIO."})
                return 1
            store.update(job_id, "success", result)
            return 0
        except Exception as exc:
            with logpath.open("a") as log:
                log.write(f"\nCloudOps observation failed: {type(exc).__name__}\n")
            message = str(exc) if isinstance(exc, CloudOpsError) else "Worker failed. Inspect the host journal."
            store.update(job_id, "attention" if job["mutating"] else "failed", {"error": message})
            return 1

if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1]))
    except (CloudOpsError, IndexError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
