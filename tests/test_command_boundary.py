import os,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]

@pytest.mark.parametrize('command',['','bash','check extra','backup; id','backup\nid','backup && id','scp -t /tmp/file','sftp','deploy --force','$(id)','/bin/sh'])
def test_actual_gateway_process_rejects_unapproved_input(command):
    # All inputs are rejected before sudo is invoked. No host operation executes.
    result=subprocess.run([sys.executable,'-I',str(ROOT/'bin/cloudops-ssh-gateway')],env={'PATH':'/usr/bin:/bin','SSH_ORIGINAL_COMMAND':command},capture_output=True,text=True)
    assert result.returncode==64
    assert 'fixed CloudOps operations' in result.stderr

@pytest.mark.parametrize('args',[[],['backup','extra'],['upgrade'],['backup; id']])
def test_actual_host_script_rejects_unapproved_argv(args):
    result=subprocess.run(['/bin/sh',str(ROOT/'bin/cloudops-host'),*args],capture_output=True,text=True)
    assert result.returncode==64
