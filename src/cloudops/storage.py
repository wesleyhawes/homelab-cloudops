"""Mount identity checks run before writes AND in Docker's systemd startup path."""
from __future__ import annotations
import json
import os
from pathlib import Path
from .errors import CloudOpsError
from .util import run


def mount_identity(path: str) -> dict:
    result = run(["findmnt", "--json", "--mountpoint", path, "--output", "TARGET,SOURCE,FSTYPE,UUID"], check=False)
    if result.returncode:
        raise CloudOpsError(f"Required storage is not mounted at {path}. No directory will be created in its place.")
    try:
        entries = json.loads(result.stdout)["filesystems"]
        if len(entries) != 1 or entries[0]["target"] != path:
            raise ValueError("not an exact mount")
        item = entries[0]
        return {"uuid": item.get("uuid") or "", "source": item["source"], "fstype": item["fstype"]}
    except (KeyError, ValueError, TypeError) as exc:
        raise CloudOpsError(f"Cannot establish storage identity for {path}.") from exc


def verify_identity(expected: dict, actual: dict, name: str) -> None:
    if not expected or not (expected.get("uuid") or expected.get("source")):
        raise CloudOpsError(f"{name} has not been enrolled. Re-run guided configuration on the target host.")
    key = "uuid" if expected.get("uuid") else "source"
    if expected.get(key) != actual.get(key) or expected.get("fstype") != actual.get("fstype"):
        raise CloudOpsError(f"{name} identity changed. Refusing to use a different filesystem.")


def no_symlink(path: str) -> None:
    p = Path(path)
    for part in [p, *p.parents]:
        if part.is_symlink():
            raise CloudOpsError(f"Storage paths must not contain symbolic links: {part}")


def check_storage(config, *, backup: bool = False) -> dict:
    no_symlink(config.data_path)
    actual = mount_identity(config.data_mount)
    verify_identity(config.data_identity, actual, "Data mount")
    if actual["fstype"] not in ("ext4", "xfs"):
        raise CloudOpsError("The pilot's data filesystem must be ext4 or XFS.")
    st = os.statvfs(config.data_mount)
    free = st.f_bavail * st.f_frsize
    if free < config.minimum_free_gib * 1024**3:
        raise CloudOpsError("Data storage is below the configured free-space reserve.")
    if st.f_files and st.f_favail / st.f_files < 0.02:
        raise CloudOpsError("Data filesystem has fewer than 2% free inodes.")
    result = {"data_free_bytes": free, "data_mount_verified": True}
    if backup:
        no_symlink(config.backup_path)
        b = mount_identity(config.backup_mount)
        verify_identity(config.backup_identity, b, "Backup mount")
        if actual.get("uuid") and actual["uuid"] == b.get("uuid") or actual["source"] == b["source"]:
            raise CloudOpsError("Backup and data cannot use the same enrolled filesystem.")
        if os.stat(config.data_mount).st_dev == os.stat(config.backup_mount).st_dev:
            raise CloudOpsError("Backup and data resolve to the same filesystem device.")
        bst = os.statvfs(config.backup_mount)
        if bst.f_bavail * bst.f_frsize < 1024**3:
            raise CloudOpsError("Backup storage has less than 1 GiB free; more may be needed for the next backup.")
        result["backup_mount_verified"] = True
    return result
