import json
from dataclasses import replace
import pytest
from cloudops.config import Config, private_ipv4, safe_path
from cloudops.errors import CloudOpsError, UnsupportedProvider
from cloudops.providers import REGISTRY, adapter_for, provider_spec

@pytest.mark.parametrize('ip',['127.0.0.1','10.10.1.9','192.168.10.5','172.31.0.10','100.100.10.1'])
def test_private_bindings(ip):
    assert private_ipv4(ip)==ip

@pytest.mark.parametrize('ip',['0.0.0.0','8.8.8.8','169.254.1.1','224.0.0.1','::1','172.32.1.1','not-an-ip'])
def test_bad_bindings(ip):
    with pytest.raises(CloudOpsError): private_ipv4(ip)

@pytest.mark.parametrize('path',['/','relative','/srv/../etc','/srv//disk','/srv/disk/','/srv/a;rm','/srv/a b','/srv/$(id)','/srv/\nfoo'])
def test_path_rejects_unsafe(path):
    with pytest.raises(CloudOpsError): safe_path(path,'data')

@pytest.mark.parametrize('change',[
 {'provider':'random'}, {'schema_version':True}, {'schema_version':2}, {'instance_id':'../../etc'},
 {'cloud_url':'http://cloud.example.com'}, {'cloud_url':'https://192.168.1.2'},
 {'cloud_url':'https://cloud.example.com/subpath'}, {'cloud_url':'https://a:b@cloud.example.com'},
 {'cloud_url':'https://cloud.example.com:8443'}, {'cloud_url':'https://bad_host.example.com'},
 {'management_port':3000}, {'management_port':True}, {'management_port':8080},
 {'data_path':'/other/data'}, {'data_path':'/srv/cloud-data'},
 {'backup_mount':'/srv/cloud-data/backups','backup_path':'/srv/cloud-data/backups/aio'},
 {'minimum_free_gib':0}, {'job_timeout_seconds':20}, {'timezone':'Never/Here'},
 {'semaphore_image':'evil/image:latest'}, {'caddy_image':'caddy:2;id'},
 {'proxy_mode':'public-auto'}, {'data_identity':{'password':'do-not-accept'}},
 {'not_a_field':True}, {'data_identity':[]}, {'data_identity':{'uuid':3}},
])
def test_strict_config(change,config):
    with pytest.raises(CloudOpsError): Config.from_dict(config.to_dict()|change)

def test_roundtrip(tmp_path,config):
    path=tmp_path/'config.json';path.write_text(json.dumps(config.to_dict()))
    assert Config.load(path)==config

@pytest.mark.parametrize('name',['owncloud_ocis','owncloud_server','oxicloud'])
def test_future_providers_fail_before_any_execution(name,config,tmp_path):
    c=replace(config,provider=name).validate()
    assert REGISTRY[name].maturity=='planned'
    with pytest.raises(UnsupportedProvider): provider_spec(name,'deploy')
    with pytest.raises(UnsupportedProvider): adapter_for(c,tmp_path)
    assert list(tmp_path.iterdir())==[]

def test_no_arbitrary_adapter_import(config,tmp_path):
    with pytest.raises(UnsupportedProvider): provider_spec('os.system')

def test_capability_denial():
    with pytest.raises(UnsupportedProvider): provider_spec('nextcloud_aio','format_disk')
