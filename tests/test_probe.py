import hashlib,json
from dataclasses import replace
from unittest.mock import patch,Mock
import pytest
from cloudops.probe import WebDAVProbe,PinnedHTTPS
from cloudops.errors import CloudOpsError

@pytest.fixture
def probe(tmp_path,config):
    secret=tmp_path/'secret.json';secret.write_text(json.dumps({'username':'probe','app_password':'secret-for-test-only'}))
    return WebDAVProbe(config,secret,tmp_path/'probe-manifest.json')

def manifest(probe,source='primary'):
    data=b'x'*512
    probe.manifest_file.write_text(json.dumps({'provider':probe.config.provider,'cloud_url':probe.config.cloud_url,'source_machine':source,'filename':'cloudops-recovery-probe-test.bin','bytes':512,'sha256':hashlib.sha256(data).hexdigest()}))
    return data

def test_enroll_no_overwrite_or_secret_leak(probe):
    calls=[];content=None
    def request(method,name,**kw):
        nonlocal content
        calls.append((method,name,kw));content=kw.get('content',content)
        return (201,b'') if method=='PUT' else ((401,b'') if kw.get('anonymous') else (200,content))
    with patch.object(probe,'request',side_effect=request),patch('cloudops.probe.machine_identity',return_value='primary'):
        result=probe.enroll()
        with pytest.raises(CloudOpsError):probe.enroll()
    assert not result['restore_verified'] and len([x for x in calls if x[0]=='PUT'])==1
    assert 'secret-for-test-only' not in probe.manifest_file.read_text()

def test_cannot_claim_restore_on_primary(probe):
    manifest(probe)
    with patch('cloudops.probe.machine_identity',return_value='primary'),pytest.raises(CloudOpsError):probe.verify(recovery=True)

def test_cannot_claim_restore_on_clone_with_same_machineid(probe):
    manifest(probe);probe.config=replace(probe.config,mode='recovery-test')
    with patch('cloudops.probe.machine_identity',return_value='primary'),pytest.raises(CloudOpsError):probe.verify(recovery=True)

def test_recovery_verifies_original_bytes_and_denial(probe):
    data=manifest(probe);probe.config=replace(probe.config,mode='recovery-test')
    with patch('cloudops.probe.machine_identity',return_value='recovery'),patch.object(probe,'request',side_effect=[(200,data),(401,b'')]):r=probe.verify(recovery=True)
    assert r['restore_verified'] and r['file_checksum_verified'] and r['anonymous_access_denied']
    assert 'not all files' in r['scope']

@pytest.mark.parametrize('responses',[[(200,b'wrong')],[(404,b'')],[(200,b'x'*512),(200,b'x'*512)]])
def test_corrupt_missing_or_public_file_fails(probe,responses):
    manifest(probe)
    with patch.object(probe,'request',side_effect=responses),pytest.raises(CloudOpsError):probe.verify(recovery=False)

def test_no_fresh_probe_on_recovery(probe):
    probe.config=replace(probe.config,mode='recovery-test')
    with pytest.raises(CloudOpsError):probe.enroll()

def test_recovery_connection_pins_destination_but_keeps_tls_hostname():
    context=Mock();context.post_handshake_auth=None
    with patch('cloudops.probe.socket.create_connection',return_value='raw') as create:
        connection=PinnedHTTPS('cloud.example.com','192.168.1.80',context);connection.connect()
    assert create.call_args.args[0]==('192.168.1.80',443)
    context.wrap_socket.assert_called_once_with('raw',server_hostname='cloud.example.com')
