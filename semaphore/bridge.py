#!/usr/bin/env python3
"""Temporary private-key copy satisfies OpenSSH permissions without host-wide access."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ALLOWED = {"check", "deploy", "backup", "backup_check", "verify", "recovery_info", "verify_recovery"}
if len(sys.argv) != 2 or sys.argv[1] not in ALLOWED:
    raise SystemExit(64)
with tempfile.TemporaryDirectory(prefix="cloudops-key-") as directory:
    key = Path(directory) / "id_ed25519"
    key.write_bytes(Path("/run/secrets/bridge_key").read_bytes())
    key.chmod(0o600)
    args = ["ssh", "-T", "-i", str(key), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
            "-o", "StrictHostKeyChecking=yes", "-o", "UserKnownHostsFile=/opt/cloudops-known-hosts",
            "-o", "HostKeyAlias=cloudops-host", "-o", "ConnectTimeout=15",
            "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=4",
            "cloudops-bridge@cloudops-host", sys.argv[1]]
    raise SystemExit(subprocess.call(args))
