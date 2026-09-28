from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from ..backup_evidence import validate_evidence
from ..errors import CloudOpsError
from ..storage import check_storage
from ..util import atomic_json, now, run
from ..render import aio_compose

MASTER = "nextcloud-aio-mastercontainer"
BORG = "nextcloud-aio-borgbackup"
ARCHIVES = "/mnt/docker-aio-config/data/backup_archives.list"


class NextcloudAIO:
    """AIO owns its child containers. No private write API is used."""
    def __init__(self, config, state: Path):
        self.config = config
        self.state = state

    def inspect(self, name: str) -> dict | None:
        proc = run(["docker", "inspect", name], check=False)
        if proc.returncode:
            return None
        try:
            return json.loads(proc.stdout)[0]
        except (ValueError, IndexError, TypeError) as exc:
            raise CloudOpsError("Unexpected Docker inspect output.") from exc

    def archives(self) -> set[str]:
        proc = run(["docker", "exec", MASTER, "cat", ARCHIVES], check=False)
        if proc.returncode:
            return set()
        return {line.split(",", 1)[0] for line in proc.stdout.splitlines() if "nextcloud-aio" in line}

    def idle(self) -> None:
        for name in (BORG, "nextcloud-aio-watchtower"):
            obj = self.inspect(name)
            if obj and obj.get("State", {}).get("Running"):
                raise CloudOpsError(f"{name} is busy. Do not start a competing operation.")
        result = run(["docker", "exec", MASTER, "test", "-e", "/mnt/docker-aio-config/data/daily_backup_running"], check=False)
        if result.returncode == 0:
            raise CloudOpsError("AIO reports an active or interrupted native maintenance operation. Inspect AIO.")
        if result.returncode != 1:
            raise CloudOpsError("Cannot establish AIO maintenance state.")

    def assert_owned(self) -> dict:
        marker = self.state / "deployment.json"
        if not marker.exists():
            raise CloudOpsError("This AIO installation is not enrolled as a CloudOps deployment.")
        data = json.loads(marker.read_text())
        if data.get("provider") != self.config.provider or data.get("data_path") != self.config.data_path or data.get("instance_id") != self.config.instance_id:
            raise CloudOpsError("Provider or data-path changes require an explicit migration; refusing in-place replacement.")
        return data

    def health(self, *, require_healthy: bool = False) -> dict:
        obj = self.inspect(MASTER)
        result = {"provider": "nextcloud_aio", "checked_at": now(), "cloud_url": self.config.cloud_url,
                  "master_running": bool(obj and obj.get("State", {}).get("Running")),
                  "application_verified": False, "restore_verified": False}
        if not result["master_running"]:
            if require_healthy:
                raise CloudOpsError("AIO mastercontainer is not running.")
            return result
        status = run(["docker", "exec", "--user", "www-data", "nextcloud-aio-nextcloud", "php", "occ", "status", "--output=json"], check=False)
        if status.returncode == 0:
            try:
                nc = json.loads(status.stdout)
                good = nc.get("installed") is True and nc.get("maintenance") is False and nc.get("needsDbUpgrade") is False
                result.update(application_verified=good, version=nc.get("versionstring"), maintenance=nc.get("maintenance"))
            except (ValueError, TypeError):
                pass
        if require_healthy and not result["application_verified"]:
            raise CloudOpsError("Nextcloud has not passed its installed/maintenance/database checks. Complete onboarding or inspect AIO.")
        return result

    def preflight(self, *, backup: bool = False) -> dict:
        result = check_storage(self.config, backup=backup)
        run(["docker", "info", "--format", "{{.ServerVersion}}"])
        run(["docker", "compose", "version", "--short"])
        return result

    def prepare_deploy(self) -> dict:
        self.preflight()
        existing = self.inspect(MASTER)
        marker = self.state / "deployment.json"
        if existing and not marker.exists():
            raise CloudOpsError("An existing unmanaged AIO was found. Automatic adoption is intentionally disabled.")
        if marker.exists():
            self.assert_owned()
        if not existing:
            # Never silently attach an old AIO metadata volume to a fresh installation.
            old = run(["docker", "volume", "inspect", "nextcloud_aio_mastercontainer"], check=False)
            if old.returncode == 0 and not marker.exists():
                raise CloudOpsError("Existing AIO metadata volume found. Use the recovery procedure, not a fresh deployment.")
        path = Path(self.config.data_path)
        if not marker.exists() and path.exists() and any(path.iterdir()):
            raise CloudOpsError("The selected data directory is not empty. Refusing to adopt or overwrite existing files.")
        path.mkdir(mode=0o750, parents=True, exist_ok=True)
        output = Path("/etc/cloudops/nextcloud.compose.yaml")
        desired = aio_compose(self.config)
        if not output.exists():
            atomic_json(output, desired)
        elif not marker.exists():
            atomic_json(output, desired)
        # Persist intent before launch so a failed launch is recoverable without adopting arbitrary volumes.
        if not marker.exists():
            atomic_json(marker, {"provider": self.config.provider, "instance_id": self.config.instance_id,
                "data_path": self.config.data_path, "created_at": now(), "status": "prepared"})
        return {"prepared": True, "existing_master": bool(existing)}

    def finish_deploy(self) -> dict:
        obj = self.inspect(MASTER)
        if not obj or not obj.get("State", {}).get("Running"):
            raise CloudOpsError("The mastercontainer did not start.")
        data = self.assert_owned()
        data.update(status="onboarding_required", observed_image_id=obj.get("Image"))
        atomic_json(self.state / "deployment.json", data)
        return {"master_running": True, "onboarding_required": True,
            "message": "Open the private AIO interface to select the application hostname and initialize backup settings.",
            "aio_url": f"https://{self.config.management_ip}:{self.config.aio_admin_port}"}

    def backup(self, mode: str = "backup") -> dict:
        self.assert_owned()
        self.preflight(backup=True)
        self.idle()
        self.health(require_healthy=True)
        before = self.inspect(BORG)
        if not before:
            raise CloudOpsError("Configure AIO's local backup destination and complete its first backup in the AIO interface first.")
        mounts = before.get("Mounts", [])
        sources = [m.get("Source") for m in mounts if m.get("Destination") == "/mnt/borgbackup"]
        if sources != [self.config.backup_path]:
            raise CloudOpsError("AIO's configured backup mount does not match the enrolled CloudOps backup path.")
        env = dict(item.split("=", 1) for item in before.get("Config", {}).get("Env", []) if "=" in item)
        if env.get("BORG_REMOTE_REPO"):
            raise CloudOpsError("This pilot verifies local mounted backup destinations only. Remote Borg support is a later adapter extension.")
        before_archives = self.archives()
        started = now()
        argv = ["docker", "exec", "--env", "AUTOMATIC_UPDATES=0", "--env", f"DAILY_BACKUP={int(mode == 'backup')}",
                "--env", f"CHECK_BACKUP={int(mode == 'check')}", "--env", "START_CONTAINERS=1", "--env", "STOP_CONTAINERS=0", MASTER, "/daily-backup.sh"]
        invocation = run(argv, timeout=self.config.job_timeout_seconds, check=False)
        # CHECK_BACKUP is asynchronous upstream; wait for a fresh stopped Borg instance.
        deadline = time.monotonic() + self.config.job_timeout_seconds
        after = None
        while time.monotonic() < deadline:
            after = self.inspect(BORG)
            fresh = after and (not before or after.get("Id") != before.get("Id") or after.get("State", {}).get("StartedAt") != before.get("State", {}).get("StartedAt"))
            if fresh and not after.get("State", {}).get("Running"):
                break
            if mode == "backup" and not fresh:
                raise CloudOpsError("AIO returned without creating fresh Borg evidence. Inspect its onboarding and backup settings.")
            time.sleep(3)
        else:
            raise CloudOpsError("Borg operation did not complete within the configured observation window. It may still be running; inspect AIO.")
        logs = run(["docker", "logs", "--since", started, BORG], check=False)
        evidence = validate_evidence(before=before, after=after, started_at=started, before_archives=before_archives,
            after_archives=self.archives(), logs=logs.stdout + logs.stderr, mode=mode)
        if invocation.returncode:
            raise CloudOpsError("Fresh backup evidence exists, but the AIO orchestration command failed; inspect application startup before acknowledging success.")
        # A backup can be valid while restart fails: preserve evidence before testing service recovery.
        atomic_json(self.state / ("last-backup.json" if mode == "backup" else "last-integrity.json"), evidence)
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            if self.health().get("application_verified"):
                return evidence | {"application_verified": True}
            time.sleep(5)
        raise CloudOpsError("Backup evidence was saved, but Nextcloud did not pass startup checks. Inspect AIO; do not retry blindly.")

    def check(self) -> dict:
        storage = self.preflight()
        result = self.health() | storage
        for name, key in (("last-backup.json", "last_backup"), ("last-integrity.json", "last_integrity"), ("last-restore-test.json", "last_restore_test")):
            path = self.state / name
            result[key] = json.loads(path.read_text()) if path.exists() else None
        return result

    def recovery_info(self) -> dict:
        return {"provider": self.config.provider, "mode": self.config.mode, "cloud_url": self.config.cloud_url,
            "data_path": self.config.data_path, "backup_path": self.config.backup_path,
            "recovery_requires": ["AIO Borg repository including its config", "Borg passphrase saved outside this cloud",
                "A separate recovery host with isolated DNS/network", "Probe manifest and separate probe credentials", "Manager recovery kit"],
            "restore_mode": "Guided AIO restore; no destructive one-click restore is exposed in this pilot.",
            "instructions": "See docs/RECOVERY.md in the release package. A backup is not a completed restore test."}

    def verify_recovery(self) -> dict:
        from ..probe import WebDAVProbe
        self.preflight()
        self.health(require_healthy=True)
        return WebDAVProbe(self.config, Path("/etc/cloudops/secrets/probe.json"), self.state / "probe-manifest.json").verify(recovery=True)
