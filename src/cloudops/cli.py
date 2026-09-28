"""Operator interface; importing this module never changes the host."""
from __future__ import annotations
import argparse
import getpass
import json
import os
import sys
import tarfile
import time
from pathlib import Path
from . import __version__, paths
from .config import Config
from .errors import CloudOpsError
from .jobs import JobStore, OPERATIONS
from .providers import REGISTRY, provider_spec
from .util import atomic_json, now, require_root, result_line, run


def follow(store: JobStore, job_id: str) -> int:
    offset = 0
    log = store.directory(job_id) / "output.log"
    while True:
        if log.exists():
            with log.open() as stream:
                stream.seek(offset)
                chunk = stream.read(65536)
                offset = stream.tell()
                if chunk:
                    print(chunk, end="", flush=True)
        job = store.get(job_id)
        if job["status"] not in {"queued", "running"}:
            # Drain any final output, then emit a structured non-secret result for the portal.
            if log.exists():
                with log.open() as stream:
                    stream.seek(offset)
                    print(stream.read(), end="", flush=True)
            print(result_line({"job_id": job_id, "status": job["status"], **job["result"]}), flush=True)
            return 0 if job["status"] == "success" else 1
        time.sleep(1)


def submit(operation: str, *, wait: bool = True) -> int:
    require_root()
    config = Config.load(paths.CONFIG)
    provider_spec(config.provider, operation)
    store = JobStore(paths.STATE)
    job = store.create(operation)
    directory = store.directory(job["id"])
    argv = ["systemd-run", "--quiet", "--collect", "--unit", "cloudops-" + job["id"],
            "--property=Type=exec", "--property=UMask=0077", "--property=Restart=no",
            str(paths.VENV / "bin/python"), "-I", "-m", "cloudops.worker", job["id"]]
    try:
        run(argv)
    except CloudOpsError:
        store.update(job["id"], "failed", {"error": "The host could not start the systemd job."})
        raise
    print(f"Job {job['id']} started on this server. Browser/SSH disconnects do not cancel the service.", flush=True)
    if wait:
        return follow(store, job["id"])
    print(result_line({"job_id": job["id"], "status": "queued"}))
    return 0


def recovery_export(destination: Path) -> int:
    require_root()
    if destination.exists():
        raise CloudOpsError("Refusing to overwrite an existing recovery kit.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    old = os.umask(0o077)
    try:
        with tarfile.open(destination, "w:gz") as tar:
            # Deliberately excludes credentials, manager DB and all cloud files.
            for source, arc in ((paths.CONFIG, "config.json"), (paths.STATE / "probe-manifest.json", "probe-manifest.json"),
                                (paths.STATE / "deployment.json", "deployment.json"),
                                (paths.STATE / "last-backup.json", "last-backup.json"),
                                (paths.RELEASE / "docs/RECOVERY.md", "RECOVERY.md")):
                if source.exists():
                    tar.add(source, arcname=arc, recursive=False)
    finally:
        os.umask(old)
    print(f"Wrote {destination}. This is a NON-SECRET configuration kit, NOT a backup of cloud data or manager credentials.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cloudctl", description="Standalone homelab cloud operations")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("providers", help="Show implemented and planned adapters")
    valid = commands.add_parser("validate", help="Validate configuration without changing the host")
    valid.add_argument("file", type=Path)
    render = commands.add_parser("render", help="Generate preview Compose files without deploying")
    render.add_argument("file", type=Path)
    render.add_argument("--output", type=Path, required=True)
    op = commands.add_parser("run", help="Start a persistent server-side operation")
    op.add_argument("operation", choices=sorted(OPERATIONS))
    op.add_argument("--detach", action="store_true")
    commands.add_parser("history")
    watch = commands.add_parser("follow")
    watch.add_argument("job_id")
    commands.add_parser("guard-storage")
    commands.add_parser("provision-ui")
    commands.add_parser("probe-credentials")
    commands.add_parser("probe-enroll")
    manager = commands.add_parser("manager-backup", help="Root-only plaintext manager snapshot; contains secrets")
    manager.add_argument("destination", type=Path)
    exp = commands.add_parser("export-recovery")
    exp.add_argument("destination", type=Path)
    ack = commands.add_parser("acknowledge")
    ack.add_argument("job_id")
    commands.add_parser("enable-backup-timer")
    try:
        args = parser.parse_args(argv)
        if args.command == "providers":
            print(json.dumps([vars(item) for item in REGISTRY.values()], indent=2))
            return 0
        if args.command == "validate":
            c = Config.load(args.file)
            print(f"Configuration valid. Provider: {c.provider}; readiness: {REGISTRY[c.provider].maturity}.")
            return 0
        if args.command == "render":
            from .render import render_all
            render_all(Config.load(args.file), args.output)
            print(f"Rendered preview to {args.output}; nothing was deployed.")
            return 0
        require_root()
        if args.command == "run":
            return submit(args.operation, wait=not args.detach)
        if args.command == "history":
            print(json.dumps(JobStore(paths.STATE).list(), indent=2))
            return 0
        if args.command == "follow":
            return follow(JobStore(paths.STATE), args.job_id)
        config = Config.load(paths.CONFIG)
        if args.command == "guard-storage":
            from .storage import check_storage
            check_storage(config)
            return 0
        if args.command == "provision-ui":
            from .semaphore_api import SemaphoreAPI, provision
            api = SemaphoreAPI()
            api.login(Path("/etc/cloudops/secrets/admin_password").read_text().strip())
            provision(api, config, Path("/etc/cloudops/public/portal.json"))
            print("Browser operations configured from local playbooks. No Git account was used.")
            return 0
        if args.command == "probe-credentials":
            username = input("Dedicated Nextcloud probe username: ").strip()
            password = getpass.getpass("Its app password (not printed): ")
            if not username or not password:
                raise CloudOpsError("Both credentials are required.")
            atomic_json(Path("/etc/cloudops/secrets/probe.json"), {"username": username, "app_password": password})
            print("Probe credential saved outside the cloud and outside job logs.")
            return 0
        if args.command == "probe-enroll":
            from .probe import WebDAVProbe
            from .providers.nextcloud import NextcloudAIO
            NextcloudAIO(config, paths.STATE).health(require_healthy=True)
            print(result_line(WebDAVProbe(config, Path("/etc/cloudops/secrets/probe.json"), paths.STATE / "probe-manifest.json").enroll()))
            return 0
        if args.command == "manager-backup":
            from .manager_backup import snapshot
            print(json.dumps(snapshot(args.destination), indent=2))
            return 0
        if args.command == "export-recovery":
            return recovery_export(args.destination)
        if args.command == "acknowledge":
            from .providers.nextcloud import NextcloudAIO
            store = JobStore(paths.STATE)
            job = store.get(args.job_id)
            unit = run(["systemctl", "is-active", "cloudops-" + args.job_id], check=False)
            if unit.stdout.strip() in {"active", "activating", "deactivating"}:
                raise CloudOpsError("The job service is still active; it cannot be acknowledged.")
            if job["status"] not in {"attention", "queued", "running"}:
                raise CloudOpsError("Only interrupted or attention-required jobs can be acknowledged.")
            adapter = NextcloudAIO(config, paths.STATE)
            for container in ("nextcloud-aio-borgbackup", "nextcloud-aio-watchtower"):
                observed = adapter.inspect(container)
                if observed and observed.get("State", {}).get("Running"):
                    raise CloudOpsError("Native AIO maintenance is still active; acknowledgement is blocked.")
            master = adapter.inspect("nextcloud-aio-mastercontainer")
            if master and master.get("State", {}).get("Running"):
                adapter.idle()
            if input("After inspecting AIO and storage, type the full job ID to unblock maintenance: ") != args.job_id:
                raise CloudOpsError("Confirmation did not match.")
            store.update(args.job_id, "acknowledged", {"message": "Operator acknowledged interruption; not marked successful.", "at": now()})
            return 0
        if args.command == "enable-backup-timer":
            evidence = paths.STATE / "last-backup.json"
            if not evidence.exists() or not json.loads(evidence.read_text()).get("backup_verified"):
                raise CloudOpsError("First complete a verified CloudOps backup. Native-only backups do not satisfy this gate.")
            if input("Disable AIO's native daily schedule first. Type ENABLE to authorize the host's daily 03:00 backup: ") != "ENABLE":
                raise CloudOpsError("Backup scheduling was not approved.")
            run(["systemctl", "enable", "--now", "cloudops-backup.timer"])
            return 0
        return 1
    except CloudOpsError as exc:
        print(f"CloudOps: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
