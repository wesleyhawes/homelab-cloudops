import copy
import pytest
from cloudops.backup_evidence import validate_evidence,dt
from cloudops.errors import CloudOpsError

@pytest.fixture
def evidence():
    return dict(before={'Id':'old','State':{'StartedAt':'2026-09-27T03:00:00Z'}},
      after={'Id':'new','Config':{'Env':['BORG_MODE=backup']},'State':{'Status':'exited','Running':False,'ExitCode':0,'StartedAt':'2026-09-28T03:00:01Z','FinishedAt':'2026-09-28T03:05:00Z'}},
      started_at='2026-09-28T03:00:00Z',before_archives={'old'},after_archives={'old','new'},logs='Backup finished successfully on Monday',mode='backup')

def test_fresh_backup_requires_all_evidence(evidence):
    r=validate_evidence(**evidence)
    assert r['backup_verified'] is True and r['restore_verified'] is False and r['new_archives']==['new']

@pytest.mark.parametrize('field,value',[('Running',True),('Status','running'),('ExitCode',1),('StartedAt','2026-09-27T03:00:00Z'),('FinishedAt','2026-09-28T02:00:00Z'),('StartedAt','bad')])
def test_bad_container_state_fails(evidence,field,value):
    evidence['after']['State'][field]=value
    with pytest.raises(CloudOpsError):validate_evidence(**evidence)

@pytest.mark.parametrize('change',[{'logs':''},{'after_archives':{'old'}},{'mode':'restore'}])
def test_exit_zero_is_not_sufficient(evidence,change):
    evidence.update(change)
    with pytest.raises(CloudOpsError):validate_evidence(**evidence)

def test_old_success_not_reused(evidence):
    evidence['before']=copy.deepcopy(evidence['after'])
    with pytest.raises(CloudOpsError):validate_evidence(**evidence)

def test_wrong_mode_rejected(evidence):
    evidence['after']['Config']['Env']=['BORG_MODE=restore']
    with pytest.raises(CloudOpsError):validate_evidence(**evidence)

def test_integrity_check_not_marked_as_backup_or_restore(evidence):
    evidence.update(mode='check',logs='Check finished successfully on Monday',after_archives={'old'})
    evidence['after']['Config']['Env']=['BORG_MODE=check']
    r=validate_evidence(**evidence)
    assert r['integrity_verified'] and not r['backup_verified'] and not r['restore_verified']

@pytest.mark.parametrize('value',['2026-09-28',None,'bad',123])
def test_timestamp_requires_timezone(value):
    with pytest.raises(CloudOpsError):dt(value)
