"""A tiny, separately credentialed WebDAV probe. No user documents are enumerated."""
from __future__ import annotations
import base64
import hashlib
import http.client
import json
import secrets
import socket
import ssl
from pathlib import Path
from urllib.parse import quote, urlsplit
from .errors import CloudOpsError
from .util import atomic_json, now


def machine_identity() -> str:
    return hashlib.sha256(Path("/etc/machine-id").read_bytes().strip()).hexdigest()


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname: str, target: str | None, context):
        super().__init__(hostname, 443, timeout=30, context=context)
        self.target = target

    def connect(self):
        if not self.target:
            return super().connect()
        # Connect only to the local recovery host; still validate TLS for the original cloud hostname.
        raw = socket.create_connection((self.target, 443), self.timeout)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


class WebDAVProbe:
    def __init__(self, config, secret_file: Path, manifest_file: Path):
        self.config, self.secret_file, self.manifest_file = config, secret_file, manifest_file

    def credentials(self) -> dict:
        try:
            data = json.loads(self.secret_file.read_text())
            if set(data) != {"username", "app_password"} or not all(isinstance(v, str) and v for v in data.values()):
                raise ValueError("invalid fields")
            return data
        except (OSError, ValueError, TypeError) as exc:
            raise CloudOpsError("Configure the dedicated WebDAV probe account and app password using cloudctl probe-credentials.") from exc

    def request(self, method: str, filename: str, *, content: bytes | None = None, anonymous: bool = False):
        data = self.credentials()
        host = urlsplit(self.config.cloud_url).hostname
        uri = "/remote.php/dav/files/" + quote(data["username"], safe="") + "/" + quote(filename, safe="")
        context = ssl.create_default_context()
        ca = Path("/etc/cloudops/probe-ca.pem")
        if ca.exists():
            context.load_verify_locations(cafile=str(ca))
        target = self.config.management_ip if self.config.mode == "recovery-test" else None
        headers = {"Content-Type": "application/octet-stream", "User-Agent": "CloudOps-recovery-probe/0.1"}
        if not anonymous:
            headers["Authorization"] = "Basic " + base64.b64encode((data["username"] + ":" + data["app_password"]).encode()).decode()
        if method == "PUT":
            headers["If-None-Match"] = "*"
        connection = PinnedHTTPS(host, target, context)
        try:
            connection.request(method, uri, body=content, headers=headers)
            response = connection.getresponse()
            body = response.read(65537)
            if len(body) > 65536:
                raise CloudOpsError("Probe response exceeded its safety limit.")
            return response.status, body
        except (OSError, http.client.HTTPException) as exc:
            raise CloudOpsError("WebDAV probe connection or TLS validation failed. Check routing, trusted certificates and the dedicated account.") from exc
        finally:
            connection.close()

    def enroll(self) -> dict:
        if self.config.mode != "primary":
            raise CloudOpsError("Do not create new probe data on the recovery host. Import the original manifest.")
        if self.manifest_file.exists():
            raise CloudOpsError("A probe manifest already exists. Preserve it across backup/restore tests.")
        content = secrets.token_bytes(512)
        filename = "cloudops-recovery-probe-" + secrets.token_hex(12) + ".bin"
        status, _ = self.request("PUT", filename, content=content)
        if status != 201:
            raise CloudOpsError("Probe creation did not return HTTP 201; no existing file was intentionally overwritten.")
        manifest = {"schema_version": 1, "provider": self.config.provider, "cloud_url": self.config.cloud_url,
                    "source_machine": machine_identity(), "filename": filename, "sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content), "created_at": now()}
        atomic_json(self.manifest_file, manifest)
        return self.verify(recovery=False)

    def verify(self, *, recovery: bool) -> dict:
        try:
            manifest = json.loads(self.manifest_file.read_text())
        except (OSError, ValueError) as exc:
            raise CloudOpsError("Import or create a probe manifest before running file verification.") from exc
        if manifest.get("provider") != self.config.provider or manifest.get("cloud_url") != self.config.cloud_url:
            raise CloudOpsError("Probe provider or hostname does not match this deployment.")
        if recovery:
            if self.config.mode != "recovery-test" or manifest.get("source_machine") == machine_identity():
                raise CloudOpsError("Recovery verification requires a distinct recovery-test host, not the primary server.")
        filename = manifest.get("filename", "")
        if not isinstance(filename, str) or not filename.startswith("cloudops-recovery-probe-") or "/" in filename or len(filename) > 100:
            raise CloudOpsError("Invalid probe filename.")
        status, body = self.request("GET", filename)
        if status != 200 or len(body) != manifest.get("bytes") or hashlib.sha256(body).hexdigest() != manifest.get("sha256"):
            raise CloudOpsError("Recovered probe content does not match the original file.")
        anonymous_status, _ = self.request("GET", filename, anonymous=True)
        if anonymous_status not in (401, 403, 404):
            raise CloudOpsError("Anonymous access to the private probe was not denied as expected.")
        return {"verified_at": now(), "file_checksum_verified": True, "anonymous_access_denied": True,
                "restore_verified": recovery, "scope": "Dedicated probe account and one seeded file; not all files, shares or permissions.",
                "source_machine": manifest["source_machine"], "verification_machine": machine_identity()}
