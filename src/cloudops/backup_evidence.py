"""Fresh evidence, not merely docker-exec's exit status, establishes success."""
from datetime import datetime, timezone
from .errors import CloudOpsError


def dt(value: str) -> datetime:
    # Docker emits nanoseconds; datetime accepts/truncates these to microseconds.
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise CloudOpsError("Invalid timestamp in backup evidence.") from exc


def validate_evidence(*, before: dict | None, after: dict, started_at: str,
                      before_archives: set[str], after_archives: set[str], logs: str,
                      mode: str) -> dict:
    state = after.get("State", {})
    env = dict(item.split("=", 1) for item in after.get("Config", {}).get("Env", []) if "=" in item)
    if mode not in ("backup", "check") or env.get("BORG_MODE") != mode:
        raise CloudOpsError("Borg ran in an unexpected mode; this is not evidence of the requested operation.")
    if state.get("Running") or state.get("Status") != "exited" or state.get("ExitCode") != 0:
        raise CloudOpsError("The fresh Borg operation did not exit successfully.")
    start = dt(state.get("StartedAt", ""))
    finish = dt(state.get("FinishedAt", ""))
    if start < dt(started_at) or finish < start:
        raise CloudOpsError("Borg evidence is stale or internally inconsistent.")
    if before and before.get("Id") == after.get("Id") and before.get("State", {}).get("StartedAt") == state.get("StartedAt"):
        raise CloudOpsError("Borg did not start a new operation.")
    marker = "Backup finished successfully on " if mode == "backup" else "Check finished successfully on "
    if marker not in logs:
        raise CloudOpsError("Expected upstream completion evidence is missing; inspect AIO before retrying.")
    new_archives = sorted(after_archives - before_archives)
    if mode == "backup" and not new_archives:
        raise CloudOpsError("No new AIO backup archive was reported. An old backup is not a successful new backup.")
    return {"operation": mode, "finished_at": finish.isoformat(), "container_id": after.get("Id"),
            "new_archives": new_archives, "backup_verified": mode == "backup",
            "integrity_verified": mode == "check", "restore_verified": False}
