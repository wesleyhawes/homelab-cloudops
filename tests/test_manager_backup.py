from unittest.mock import patch
from pathlib import Path
import pytest
from cloudops.manager_backup import snapshot
from cloudops.errors import CloudOpsError

def test_snapshot_never_overwrites(tmp_path):
    dest=tmp_path/'existing.tar.gz';dest.write_bytes(b'important')
    with patch('cloudops.manager_backup.require_root'),pytest.raises(CloudOpsError):snapshot(dest)
    assert dest.read_bytes()==b'important'

def test_snapshot_requires_absolute_path():
    with patch('cloudops.manager_backup.require_root'),pytest.raises(CloudOpsError):snapshot(Path('relative.tar.gz'))

def test_snapshot_blocks_active_work(tmp_path):
    with patch('cloudops.manager_backup.require_root'),patch('cloudops.manager_backup.JobStore') as store:
        store.return_value.list.return_value=[{'status':'running'}]
        with pytest.raises(CloudOpsError,match='active'):snapshot(tmp_path/'new.tar.gz')
