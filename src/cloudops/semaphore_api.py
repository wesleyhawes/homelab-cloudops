"""Native Semaphore API provisioning; no Git account and no permanent API token."""
from __future__ import annotations
import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from .errors import CloudOpsError
from .util import atomic_json

ACTIONS = {
    "check": ("Check my cloud", False, "Refresh application, storage and recorded recovery evidence."),
    "deploy": ("Install cloud", True, "Create the AIO mastercontainer. Complete supported native onboarding afterwards."),
    "backup": ("Back up now", True, "Briefly stop application writes, create a fresh native backup and verify completion evidence."),
    "backup_check": ("Check backup integrity", True, "Ask Borg to verify stored backup data. This is not a restore test."),
    "verify": ("Verify application", False, "Inspect installed, maintenance and database-upgrade state."),
    "recovery_info": ("Recovery instructions", False, "Show recovery prerequisites without exporting secrets."),
    "verify_recovery": ("Verify recovered files", False, "On a separate recovery-test host, check the original seeded file and anonymous denial."),
}


class SemaphoreAPI:
    def __init__(self, base: str = "http://127.0.0.1:3000"):
        self.base = base.rstrip("/")
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, method: str, path: str, data=None):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(self.base + "/api" + path, data=body, method=method, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=30) as response:
                raw = response.read(2_000_000)
                return json.loads(raw) if raw else None
        except (urllib.error.URLError, ValueError) as exc:
            # Never echo response bodies or login data into installer logs.
            raise CloudOpsError(f"Semaphore API request failed: {method} {path.split('?')[0]}. Check its service and credentials.") from exc

    def login(self, password: str):
        self.request("POST", "/auth/login", {"auth": "admin", "password": password})

    def ensure(self, endpoint: str, payload: dict, *, list_path: str | None = None, immutable: tuple[str, ...] = ()) -> dict:
        rows = self.request("GET", list_path or endpoint) or []
        matches = [r for r in rows if r.get("name") == payload["name"]]
        if len(matches) > 1:
            raise CloudOpsError(f"Duplicate Semaphore resource: {payload['name']}. Resolve explicitly.")
        if matches:
            item = matches[0]
            for field in immutable:
                if item.get(field) != payload.get(field):
                    raise CloudOpsError(f"Existing Semaphore resource {payload['name']} differs at {field}; automatic overwrite is disabled.")
            return item
        return self.request("POST", endpoint, payload)


def provision(api: SemaphoreAPI, config, output: Path) -> dict:
    project = api.ensure("/projects", {"name": "Personal Cloud", "alert": False, "max_parallel_tasks": 1}, immutable=("max_parallel_tasks",))
    prefix = f"/project/{project['id']}"
    none = api.ensure(prefix + "/keys", {"name": "Local playbooks — no Git credential", "project_id": project["id"], "type": "none"},
                      list_path=prefix + "/keys?sort=name&order=asc", immutable=("type",))
    repo = api.ensure(prefix + "/repositories", {"name": "Bundled CloudOps playbooks", "project_id": project["id"],
                      "git_url": "/opt/cloudops-playbooks", "git_branch": "main", "ssh_key_id": none["id"]},
                      list_path=prefix + "/repositories?sort=name&order=asc", immutable=("git_url",))
    inventory = api.ensure(prefix + "/inventory", {"name": "Local operation launcher", "project_id": project["id"],
                      "inventory": "[launchers]\nlocalhost ansible_connection=local\n", "type": "static", "ssh_key_id": none["id"]},
                      list_path=prefix + "/inventory?sort=name&order=asc", immutable=("inventory", "type"))
    environment = api.ensure(prefix + "/environment", {"name": "CloudOps defaults", "project_id": project["id"], "json": "{}", "env": "{}"},
                      list_path=prefix + "/environment?sort=name&order=asc")
    operations = {}
    for op, (title, confirmation, description) in ACTIONS.items():
        payload = {"name": title, "project_id": project["id"], "inventory_id": inventory["id"],
                  "repository_id": repo["id"], "environment_id": environment["id"], "playbook": op + ".yml",
                  "app": "ansible", "type": "", "arguments": "[]", "allow_override_args_in_task": False,
                  "description": description, "survey_vars": []}
        if confirmation:
            payload["survey_vars"] = [{"name": "cloudops_confirmation", "title": "Approve this operation", "type": "enum", "required": True,
                 "description": "Read the operation description; service interruption may occur.",
                 "values": [{"name": "Proceed with this operation", "value": "PROCEED"}]}]
        item = api.ensure(prefix + "/templates", payload, list_path=prefix + "/templates?sort=name&order=asc",
                          immutable=("playbook", "repository_id", "allow_override_args_in_task"))
        operations[op] = {"id": item["id"], "title": title, "confirmation": confirmation, "description": description}
    result = {"schema_version": 1, "instance_id": config.instance_id, "provider": config.provider, "mode": config.mode,
              "project_id": project["id"], "operations": operations, "cloud_url": config.cloud_url,
              "aio_url": f"https://{config.management_ip}:{config.aio_admin_port}", "release": "0.1.0a1"}
    atomic_json(output, result, mode=0o644)
    return result
