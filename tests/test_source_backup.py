import importlib.util
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location(
    'source_backup', Path(__file__).parents[1] / 'integrations/gitea/backup.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


@pytest.fixture
def repositories(tmp_path):
    source = tmp_path / 'source'
    destination = tmp_path / 'destination.git'
    source.mkdir()
    git(source, 'init', '-b', 'main')
    git(source, 'config', 'user.name', 'Test')
    git(source, 'config', 'user.email', 'test@example.com')
    git(source, 'commit', '--allow-empty', '-m', 'initial')
    subprocess.run(['git', 'init', '--bare', '--initial-branch=main', str(destination)], check=True)
    config = {'source': str(source), 'destination': str(destination),
              'state_directory': str(tmp_path / 'backup')}
    return source, destination, config


def test_backup_retains_previous_tips_and_deleted_branches(repositories):
    source, destination, config = repositories
    first = git(source, 'rev-parse', 'HEAD')
    git(source, 'branch', 'feature')
    assert module.backup(config)['verified']
    git(source, 'branch', '-D', 'feature')
    git(source, 'commit', '--allow-empty', '-m', 'next')
    second = git(source, 'rev-parse', 'HEAD')
    assert module.backup(config)['verified']
    assert git(destination, 'rev-parse', 'main') == second
    assert git(destination, 'rev-parse', 'feature') == first
    snapshots = git(destination, 'for-each-ref', '--format=%(objectname) %(refname)', module.ARCHIVE)
    assert any(line.startswith(first) and '/previous/heads/main' in line for line in snapshots.splitlines())
    assert module.backup(config)['changed_refs'] == 0


def test_unknown_destination_edit_is_preserved(repositories):
    source, destination, config = repositories
    module.backup(config)
    # Create a destination-only commit; the local backup must not overwrite it.
    tree = git(destination, 'rev-parse', 'main^{tree}')
    independent = git(destination, '-c', 'user.name=Other', '-c', 'user.email=other@example.com',
                      'commit-tree', tree, '-p', 'main', '-m', 'independent edit')
    git(destination, 'update-ref', 'refs/heads/main', independent)
    with pytest.raises(RuntimeError, match='cat-file'):
        module.backup(config)
    assert git(destination, 'rev-parse', 'main') == independent


def test_reserved_backup_tags_are_rejected(repositories):
    source, destination, config = repositories
    git(source, 'tag', 'cloudops-backup/collision')
    with pytest.raises(ValueError, match='reserved'):
        module.backup(config)
    assert git(destination, 'for-each-ref') == ''
