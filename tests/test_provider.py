from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path
import json
import pytest
from cloudops.providers.nextcloud import NextcloudAIO
from cloudops.errors import CloudOpsError

@pytest.fixture
def adapter(config,tmp_path):return NextcloudAIO(config,tmp_path)

def test_unmanaged_aio_is_not_adopted(adapter):
    with patch.object(adapter,'preflight'),patch.object(adapter,'inspect',return_value={'Id':'existing'}),pytest.raises(CloudOpsError,match='unmanaged'):adapter.prepare_deploy()

def test_old_volume_is_not_silently_reused(adapter):
    with patch.object(adapter,'preflight'),patch.object(adapter,'inspect',return_value=None),patch('cloudops.providers.nextcloud.run',return_value=SimpleNamespace(returncode=0)),pytest.raises(CloudOpsError,match='metadata volume'):adapter.prepare_deploy()

def test_changed_instance_not_adopted(adapter):
    (adapter.state/'deployment.json').write_text(json.dumps({'provider':'nextcloud_aio','instance_id':'different','data_path':adapter.config.data_path}))
    with pytest.raises(CloudOpsError):adapter.assert_owned()

def test_native_busy_operation_blocks_adapter(adapter):
    with patch.object(adapter,'inspect',return_value={'State':{'Running':True}}),pytest.raises(CloudOpsError,match='busy'):adapter.idle()

def test_stale_native_lock_blocks_adapter(adapter):
    with patch.object(adapter,'inspect',return_value=None),patch('cloudops.providers.nextcloud.run',return_value=SimpleNamespace(returncode=0)),pytest.raises(CloudOpsError):adapter.idle()

def test_missing_master_not_healthy(adapter):
    with patch.object(adapter,'inspect',return_value=None):
        assert adapter.health()['application_verified'] is False
        with pytest.raises(CloudOpsError):adapter.health(require_healthy=True)

@pytest.mark.parametrize('status',[{'installed':True,'maintenance':True,'needsDbUpgrade':False},{'installed':True,'maintenance':False,'needsDbUpgrade':True},{'installed':False,'maintenance':False,'needsDbUpgrade':False},{}])
def test_application_health_is_not_container_running(adapter,status):
    with patch.object(adapter,'inspect',return_value={'State':{'Running':True}}),patch('cloudops.providers.nextcloud.run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(status))):
        assert adapter.health()['application_verified'] is False
