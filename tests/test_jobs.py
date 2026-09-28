from concurrent.futures import ThreadPoolExecutor
import pytest
from cloudops.jobs import JobStore
from cloudops.errors import Busy,CloudOpsError

def test_persisted_job_survives_new_process_view(tmp_path):
    store=JobStore(tmp_path);job=store.create('backup')
    store.update(job['id'],'running')
    again=JobStore(tmp_path)
    assert again.get(job['id'])['status']=='running'

def test_mutations_serialize_but_checks_can_run(tmp_path):
    store=JobStore(tmp_path);store.create('backup')
    with pytest.raises(Busy):store.create('deploy')
    assert store.create('check')['status']=='queued'

def test_attention_requires_explicit_acknowledgement(tmp_path):
    store=JobStore(tmp_path);j=store.create('backup');store.update(j['id'],'attention')
    with pytest.raises(Busy):store.create('deploy')
    store.update(j['id'],'acknowledged')
    assert store.create('deploy')['status']=='queued'

def test_duplicate_tap_cooldown(tmp_path):
    store=JobStore(tmp_path);j=store.create('backup');store.update(j['id'],'success')
    with pytest.raises(Busy):store.create('backup')

def test_concurrent_admission_has_one_winner(tmp_path):
    store=JobStore(tmp_path)
    def create(_):
        try:return store.create('backup')['id']
        except Busy:return None
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(create,range(8)))
    assert sum(r is not None for r in results)==1

@pytest.mark.parametrize('op',['format_disk','backup; id','../../bin/sh','upgrade','restore'])
def test_no_arbitrary_operations(tmp_path,op):
    with pytest.raises(CloudOpsError):JobStore(tmp_path).create(op)

@pytest.mark.parametrize('jobid',['../etc/passwd','-a','f'*33,'z'*32])
def test_job_id_cannot_traverse(tmp_path,jobid):
    with pytest.raises(CloudOpsError):JobStore(tmp_path).get(jobid)
