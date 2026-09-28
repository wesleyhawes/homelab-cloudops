"""Internal fixed provider operations called by root-owned Ansible roles."""
import json
import os
import sys
from pathlib import Path
from . import paths
from .config import Config
from .errors import CloudOpsError
from .providers import provider_spec, adapter_for
from .util import atomic_json, require_root, result_line


def execute(operation: str) -> dict:
    require_root()
    config = Config.load(paths.CONFIG)
    provider_spec(config.provider)
    adapter = adapter_for(config, paths.STATE)
    if operation == "preflight":
        return adapter.preflight()
    if operation == "prepare_deploy":
        return adapter.prepare_deploy()
    if operation == "finish_deploy":
        return adapter.finish_deploy()
    if operation == "check":
        return adapter.check()
    if operation in ("backup", "backup_check"):
        return adapter.backup("backup" if operation == "backup" else "check")
    if operation == "verify":
        adapter.preflight()
        return adapter.health(require_healthy=True)
    if operation == "recovery_info":
        return adapter.recovery_info()
    if operation == "verify_recovery":
        result = adapter.verify_recovery()
        atomic_json(paths.STATE / "last-restore-test.json", result)
        return result
    raise CloudOpsError("Unknown internal provider operation.")


def main():
    try:
        operation = sys.argv[1]
        result = execute(operation)
        if operation not in ("preflight", "prepare_deploy"):
            target = os.environ.get("CLOUDOPS_RESULT_FILE")
            if target:
                candidate = Path(target)
                if not candidate.is_relative_to(paths.STATE / "jobs"):
                    raise CloudOpsError("Invalid result destination.")
                atomic_json(candidate, result)
        print(result_line(result))
        return 0
    except (CloudOpsError, IndexError) as exc:
        print(f"CloudOps: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
