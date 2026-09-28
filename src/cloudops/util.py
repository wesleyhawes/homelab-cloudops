from __future__ import annotations
import base64
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from .errors import CloudOpsError


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, data: dict, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".cloudops-", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def result_line(data: dict) -> str:
    return "CLOUDOPS_RESULT_B64=" + base64.b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()


def run(argv: list[str], *, timeout: int = 120, check: bool = True, input: str | None = None) -> subprocess.CompletedProcess:
    """Never use a shell; do not include potentially secret stdout in public exceptions."""
    try:
        result = subprocess.run(argv, text=True, input=input, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CloudOpsError(f"Command could not complete: {Path(argv[0]).name}. Inspect the host journal.") from exc
    if check and result.returncode:
        raise CloudOpsError(f"{Path(argv[0]).name} returned exit status {result.returncode}. Inspect the host journal or upstream interface.")
    return result


def require_root() -> None:
    if os.geteuid() != 0:
        raise CloudOpsError("This operation requires root on the target server. Use sudo.")
