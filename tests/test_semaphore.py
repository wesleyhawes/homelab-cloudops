from unittest.mock import patch
import json
import pytest
from cloudops.semaphore_api import SemaphoreAPI,provision,ACTIONS
from cloudops.errors import CloudOpsError

class FakeAPI(SemaphoreAPI):
    def __init__(self): self.db={};self.next=1;self.posts=0
    def request(self,method,path,data=None):
        path=path.split('?')[0]
        if method=='GET':return self.db.get(path,[])
        assert method=='POST';self.posts+=1
        row=data|{'id':self.next};self.next+=1;self.db.setdefault(path,[]).append(row);return row

def test_local_no_git_provision_idempotent(config,tmp_path):
    api=FakeAPI();path=tmp_path/'portal.json';first=provision(api,config,path);posts=api.posts
    assert provision(api,config,path)==first and api.posts==posts
    repo=api.db['/project/1/repositories'][0]
    assert repo['git_url']=='/opt/cloudops-playbooks' and not repo['git_url'].startswith('file://')
    assert len(first['operations'])==7
    assert 'password' not in path.read_text() and 'private_key' not in path.read_text()

def test_configuration_drift_is_not_overwritten(config,tmp_path):
    api=FakeAPI();provision(api,config,tmp_path/'portal.json')
    api.db['/project/1/repositories'][0]['git_url']='https://attacker.example/x.git'
    with pytest.raises(CloudOpsError):provision(api,config,tmp_path/'portal.json')

def test_duplicate_resources_fail():
    api=FakeAPI();api.db['/projects']=[{'id':1,'name':'Personal Cloud'},{'id':2,'name':'Personal Cloud'}]
    with pytest.raises(CloudOpsError):api.ensure('/projects',{'name':'Personal Cloud'})

def test_mutating_tasks_have_survey_and_no_argument_override(config,tmp_path):
    api=FakeAPI();provision(api,config,tmp_path/'portal.json')
    for t in api.db['/project/1/templates']:
        assert t['allow_override_args_in_task'] is False
        op=t['playbook'].removesuffix('.yml')
        if ACTIONS[op][1]:assert t['survey_vars'][0]['values'][0]['value']=='PROCEED'
