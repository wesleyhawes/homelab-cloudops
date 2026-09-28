import json
from dataclasses import replace
from pathlib import Path
import pytest,yaml
from cloudops.render import aio_compose,manager_compose,caddyfile,render_all
from cloudops.errors import UnsupportedProvider

def test_aio_preserves_upstream_ownership(config):
    c=aio_compose(config);services=c['services']
    assert list(services)==['nextcloud-aio-mastercontainer']
    s=services['nextcloud-aio-mastercontainer']
    assert s['environment']['APACHE_IP_BINDING']=='127.0.0.1'
    assert c['volumes']['nextcloud_aio_mastercontainer']['name']=='nextcloud_aio_mastercontainer'
    assert not any('postgres' in k for k in services)

def test_manager_has_no_socket_or_privileged_mode(config):
    c=manager_compose(config)
    for s in c['services'].values():
        assert not s.get('privileged')
        assert not any('docker.sock' in v for v in s.get('volumes',[]))
    s=c['services']['semaphore']
    assert s['ports']==['127.0.0.1:3000:3000']
    assert s['environment']['ANSIBLE_CONFIG']=='/opt/cloudops-playbooks/ansible.cfg'
    assert 'PASSWORD' not in s['environment']
    assert s['environment']['SEMAPHORE_ADMIN_PASSWORD_FILE'].startswith('/run/secrets/')

def test_private_tls_and_no_public_manager_proxy(config):
    text=caddyfile(config)
    assert 'bind 127.0.0.1' in text and 'tls internal' in text and 'admin off' in text
    assert 'Sec-Fetch-Site cross-site' in text
    assert 'CLOUDOPS_SECRET' not in text

def test_render_is_non_deploying(tmp_path,config):
    render_all(config,tmp_path)
    for name in ['manager.compose.yaml','nextcloud.compose.yaml']:
        doc=yaml.safe_load((tmp_path/name).read_text());assert doc['services']
    assert (tmp_path/'Caddyfile').exists()

@pytest.mark.parametrize('name',['owncloud_ocis','owncloud_server','oxicloud'])
def test_no_fake_compose_for_future_provider(name,config):
    with pytest.raises(UnsupportedProvider):aio_compose(replace(config,provider=name))

def test_all_packaged_yaml_is_parseable():
    root=Path(__file__).parents[1]
    for folder in ('ansible','semaphore','examples','.github','.gitea'):
        for file in (root/folder).rglob('*'):
            if file.suffix in {'.yml','.yaml'}:
                assert yaml.safe_load(file.read_text()) is not None,file

def test_mutating_launchers_require_confirmation():
    root=Path(__file__).parents[1]
    for name in ('deploy','backup','backup_check'):
        text=(root/'semaphore'/f'{name}.yml').read_text()
        assert 'cloudops_confirmation' in text and 'PROCEED' in text


def test_public_configuration_uses_directory_mount_for_atomic_updates(config):
    c=manager_compose(config)
    assert '/etc/cloudops/public:/srv/cloudops-config:ro' in c['services']['gateway']['volumes']
    assert '/etc/cloudops/portal.json:/srv/cloudops/config.json:ro' not in c['services']['gateway']['volumes']
    assert 'handle /cloudops/config.json' in caddyfile(config)
