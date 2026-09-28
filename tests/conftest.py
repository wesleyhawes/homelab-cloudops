import pytest
from cloudops.config import Config

@pytest.fixture
def config():
    return Config(data_identity={"uuid":"data-uuid","source":"/dev/vdb","fstype":"ext4"},
                  backup_identity={"uuid":"backup-uuid","source":"/dev/vdc","fstype":"ext4"})
