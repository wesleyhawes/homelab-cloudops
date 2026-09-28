"""SQLite admission + OS locks; systemd owns actual execution, not the browser."""
from __future__ import annotations
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from .errors import Busy, CloudOpsError

MUTATIONS = {"deploy", "backup", "backup_check"}
OPERATIONS = {"check", "deploy", "backup", "backup_check", "verify", "recovery_info", "verify_recovery"}
ACTIVE = {"queued", "running", "attention"}


class JobStore:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = root / "jobs.sqlite"
        with self.connect() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, operation TEXT NOT NULL, status TEXT NOT NULL,
                    mutating INTEGER NOT NULL, created REAL NOT NULL,
                    updated REAL NOT NULL, result TEXT NOT NULL DEFAULT '{}'
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_mutation
                ON jobs(mutating) WHERE mutating=1 AND status IN ('queued','running','attention');
            """)
        os.chmod(self.db, 0o600)

    def connect(self):
        conn = sqlite3.connect(self.db, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, operation: str) -> dict:
        if operation not in OPERATIONS:
            raise CloudOpsError("Operation is not allowlisted.")
        mutating = operation in MUTATIONS
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if mutating:
                active = conn.execute("SELECT id, status FROM jobs WHERE mutating=1 AND status IN ('queued','running','attention')").fetchone()
                if active:
                    raise Busy(f"Operation {active['id']} is {active['status']}. Reconnect or inspect it; do not launch a duplicate.")
                recent = conn.execute("SELECT id FROM jobs WHERE operation=? AND created>? ORDER BY created DESC LIMIT 1", (operation, time.time()-60)).fetchone()
                if recent:
                    raise Busy("A matching operation was recently submitted. Reconnect to its history instead of tapping again.")
            job_id = uuid.uuid4().hex
            moment = time.time()
            conn.execute("INSERT INTO jobs (id,operation,status,mutating,created,updated) VALUES (?,?,?,?,?,?)", (job_id,operation,"queued",int(mutating),moment,moment))
        return self.get(job_id)

    def get(self, job_id: str) -> dict:
        if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
            raise CloudOpsError("Invalid job identifier.")
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise CloudOpsError("Job not found.")
        data = dict(row)
        data["result"] = json.loads(data["result"])
        return data

    def update(self, job_id: str, status: str, result: dict | None = None) -> None:
        if status not in {"queued","running","success","failed","attention","acknowledged"}:
            raise CloudOpsError("Invalid job state.")
        with self.connect() as conn:
            conn.execute("UPDATE jobs SET status=?,updated=?,result=? WHERE id=?", (status,time.time(),json.dumps(result or {}),job_id))

    def list(self, limit: int = 30) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT id FROM jobs ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [self.get(r["id"]) for r in rows]

    def directory(self, job_id: str) -> Path:
        self.get(job_id)
        path = self.root / "jobs" / job_id
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path
