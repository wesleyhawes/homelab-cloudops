#!/usr/bin/env python3
"""One-way Git source backup, retaining previous ref tips and deleted refs."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess

ARCHIVE = 'refs/tags/cloudops-backup/'


def git(repository, *args, ssh=None):
    environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                       GIT_TERMINAL_PROMPT='0', GIT_NO_REPLACE_OBJECTS='1')
    if ssh:
        environment['GIT_SSH_COMMAND'] = ssh
    result = subprocess.run(
        ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=',
         '-C', str(repository), *args], env=environment, text=True,
        capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(f'git {args[0]} failed: {result.stderr.strip()}')
    return result.stdout.strip()


def refs(output):
    return {ref: oid for oid, ref in (line.split() for line in output.splitlines())
            if not ref.endswith('^{}')}


def sync_refs(repository, destination, source, stamp, ssh=None):
    if not source or 'refs/heads/main' not in source:
        raise ValueError('Source main branch is required')
    if any(ref.startswith(ARCHIVE) for ref in source):
        raise ValueError('Source uses the reserved backup tag namespace')
    existing = refs(git(repository, 'ls-remote', '--refs', destination,
                        'refs/heads/*', 'refs/tags/*', ssh=ssh))
    changed = {ref: oid for ref, oid in source.items() if existing.get(ref) != oid}
    if changed:
        archives = {}
        for ref, oid in changed.items():
            archives[ARCHIVE + stamp + '/incoming/' + ref[5:]] = oid
            if ref in existing:
                # Refuse to overwrite independent destination edits whose objects
                # were never present in this backup's local history.
                git(repository, 'cat-file', '-e', existing[ref])
                archives[ARCHIVE + stamp + '/previous/' + ref[5:]] = existing[ref]
        git(repository, 'push', '--atomic', destination,
            *(oid + ':' + ref for ref, oid in archives.items()), ssh=ssh)
        for ref, oid in archives.items():
            git(repository, 'update-ref', ref, oid)
        git(repository, 'push', '--atomic',
            *('--force-with-lease=' + ref + ':' + existing.get(ref, '') for ref in changed),
            destination, *(oid + ':' + ref for ref, oid in changed.items()), ssh=ssh)
    verified = refs(git(repository, 'ls-remote', '--refs', destination,
                        'refs/heads/*', 'refs/tags/*', ssh=ssh))
    if any(verified.get(ref) != oid for ref, oid in source.items()):
        raise RuntimeError('Backup ref verification failed')
    return {'source_refs': source, 'changed_refs': len(changed),
            'retained_extra_refs': len(set(verified) - set(source)), 'verified': True}


def backup(config):
    state = Path(config['state_directory'])
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state / 'backup.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        report = {'started_at_utc': stamp, 'success': False}
        try:
            repository = state / 'source.git'
            repository.mkdir(mode=0o700, exist_ok=True)
            if not (repository / 'HEAD').exists():
                git(repository, 'init', '--bare', '--initial-branch=main', '.')
            git(repository, 'fetch', '--prune', '--no-tags', config['source'],
                '+refs/heads/*:refs/heads/*', '+refs/tags/*:refs/source-tags/*')
            source = refs(git(repository, 'for-each-ref', '--format=%(objectname) %(refname)',
                              'refs/heads/', 'refs/source-tags/'))
            source = {('refs/tags/' + ref[len('refs/source-tags/'):]
                       if ref.startswith('refs/source-tags/') else ref): oid
                      for ref, oid in source.items()}
            report.update(sync_refs(repository, config['destination'], source, stamp,
                                    ssh=config.get('ssh_command')))
            report['success'] = True
            return report
        except Exception as exc:
            report['error'] = str(exc)
            raise
        finally:
            report['finished_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            runs = state / 'runs'
            runs.mkdir(mode=0o700, exist_ok=True)
            (runs / (stamp + '.json')).write_text(json.dumps(report, indent=2) + '\n')
            pending = state / 'latest.json.tmp'
            pending.write_text(json.dumps(report, indent=2) + '\n')
            pending.replace(state / 'latest.json')


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    result = backup(json.loads(args.config.read_text()))
    print(f"Backup verified: {len(result['source_refs'])} source refs, "
          f"{result['changed_refs']} updated, {result['retained_extra_refs']} retained backup refs")
