from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import json
import pytest
from cloudops import storage
from cloudops.errors import CloudOpsError

def test_exact_mount_required():
    p=SimpleNamespace(returncode=0,stdout=json.dumps({'filesystems':[{'target':'/','source':'/dev/a','fstype':'ext4','uuid':'a'}]}))
    with patch.object(storage,'run',return_value=p), pytest.raises(CloudOpsError):storage.mount_identity('/srv/cloud-data')

def test_missing_mount_no_mkdir(tmp_path):
    with patch.object(storage,'run',return_value=SimpleNamespace(returncode=1)), pytest.raises(CloudOpsError):storage.mount_identity(str(tmp_path/'missing'))
    assert not (tmp_path/'missing').exists()

def test_uuid_identity_survives_device_rename(config):
    actual=config.data_identity|{'source':'/dev/different'}
    storage.verify_identity(config.data_identity,actual,'Data')

@pytest.mark.parametrize('expected,actual',[
 ({},{'uuid':'new','fstype':'ext4'}),
 ({'uuid':'old','fstype':'ext4'},{'uuid':'new','fstype':'ext4'}),
 ({'source':'nas:/one','fstype':'nfs'},{'source':'nas:/two','fstype':'nfs'}),
 ({'uuid':'same','fstype':'ext4'},{'uuid':'same','fstype':'xfs'})])
def test_mount_change_rejected(expected,actual):
    with pytest.raises(CloudOpsError):storage.verify_identity(expected,actual,'Mount')

def test_symlink_rejected(tmp_path):
    target=tmp_path/'actual';target.mkdir();link=tmp_path/'link';link.symlink_to(target)
    with pytest.raises(CloudOpsError):storage.no_symlink(str(link/'future-data'))

@pytest.mark.parametrize('free,inodes',[(1,10000),(50*1024**3,1)])
def test_free_space_and_inode_guards(config,free,inodes):
    with patch.object(storage,'no_symlink'),patch.object(storage,'mount_identity',return_value=config.data_identity),patch.object(storage.os,'statvfs',return_value=SimpleNamespace(f_bavail=free,f_frsize=1,f_files=10000,f_favail=inodes)),pytest.raises(CloudOpsError):storage.check_storage(config)

def test_separate_backup_device_required(config):
    identities=[config.data_identity,config.backup_identity]
    st=SimpleNamespace(f_bavail=50*1024**3,f_frsize=1,f_files=10000,f_favail=5000)
    with patch.object(storage,'no_symlink'),patch.object(storage,'mount_identity',side_effect=identities),patch.object(storage.os,'statvfs',return_value=st),patch.object(storage.os,'stat',return_value=SimpleNamespace(st_dev=1)),pytest.raises(CloudOpsError):storage.check_storage(config,backup=True)

def test_valid_mounts(config):
    identities=[config.data_identity,config.backup_identity]
    st=SimpleNamespace(f_bavail=50*1024**3,f_frsize=1,f_files=10000,f_favail=5000)
    with patch.object(storage,'no_symlink'),patch.object(storage,'mount_identity',side_effect=identities),patch.object(storage.os,'statvfs',return_value=st),patch.object(storage.os,'stat',side_effect=[SimpleNamespace(st_dev=1),SimpleNamespace(st_dev=2)]):
        result=storage.check_storage(config,backup=True)
    assert result['data_mount_verified'] and result['backup_mount_verified']
