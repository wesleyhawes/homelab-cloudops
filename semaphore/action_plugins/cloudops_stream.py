"""Stream fixed host-operation output through Ansible into Semaphore task history."""
import subprocess
import sys
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _supports_check_mode = True
    _supports_async = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        operation = self._task.args.get("operation")
        allowed = {"check", "deploy", "backup", "backup_check", "verify", "recovery_info", "verify_recovery"}
        if set(self._task.args) != {"operation"} or operation not in allowed:
            return dict(result, failed=True, msg="Only a fixed CloudOps operation is accepted.")
        if self._play_context.check_mode:
            return dict(result, skipped=True, changed=False, msg="Check mode does not launch host operations.")
        process = subprocess.Popen([sys.executable, "/opt/cloudops-playbooks/bridge.py", operation],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        display = Display()
        for line in process.stdout:
            display.display(line.rstrip())
        code = process.wait()
        return dict(result, changed=operation in {"deploy","backup","backup_check"} and code == 0,
                    failed=code != 0, rc=code, msg="Inspect the streamed output above. Interrupted native work is never automatically replayed.")
