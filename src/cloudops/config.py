"""Strict, deliberately small configuration surface for the initial pilot."""
from __future__ import annotations
import ipaddress
import json
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .errors import CloudOpsError

PROVIDERS = {"nextcloud_aio", "owncloud_ocis", "owncloud_server", "oxicloud"}


def safe_path(value: str, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"/[A-Za-z0-9_./-]+", value):
        raise CloudOpsError(f"{name} must be an absolute Linux path without whitespace or shell syntax.")
    p = PurePosixPath(value)
    if ".." in p.parts or str(p) != value or value == "/":
        raise CloudOpsError(f"{name} must be a normalized, non-root absolute path.")
    return value


def private_ipv4(value: str) -> str:
    try:
        ip = ipaddress.IPv4Address(value)
    except (ipaddress.AddressValueError, TypeError) as exc:
        raise CloudOpsError("management_ip must be a specific private or loopback IPv4 address.") from exc
    permitted = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "100.64.0.0/10")]
    if not any(ip in network for network in permitted):
        raise CloudOpsError("Public, wildcard, multicast and link-local management bindings are not allowed.")
    return str(ip)


def cloud_url(value: str) -> str:
    try:
        u = urlsplit(value)
        port = u.port
    except (ValueError, TypeError) as exc:
        raise CloudOpsError("cloud_url must be https:// followed by a DNS hostname.") from exc
    if u.scheme != "https" or u.username or u.password or u.query or u.fragment or u.path not in ("", "/") or port not in (None, 443):
        raise CloudOpsError("cloud_url must use HTTPS, a hostname, port 443 and no subpath or credentials.")
    host = u.hostname or ""
    if len(host) > 253 or "." not in host or not all(re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", x) for x in host.split(".")):
        raise CloudOpsError("cloud_url needs a valid fully qualified hostname.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return "https://" + host.lower()
    raise CloudOpsError("Nextcloud AIO needs a hostname rather than a raw application IP address.")


@dataclass(frozen=True)
class Config:
    schema_version: int = 1
    instance_id: str = "personal-cloud"
    provider: str = "nextcloud_aio"
    mode: str = "primary"
    management_ip: str = "127.0.0.1"
    management_port: int = 9443
    aio_admin_port: int = 8080
    cloud_url: str = "https://cloud.example.com"
    data_mount: str = "/srv/cloud-data"
    data_path: str = "/srv/cloud-data/nextcloud"
    backup_mount: str = "/srv/cloud-backup"
    backup_path: str = "/srv/cloud-backup/aio"
    data_identity: dict = field(default_factory=dict)
    backup_identity: dict = field(default_factory=dict)
    minimum_free_gib: int = 10
    timezone: str = "UTC"
    job_timeout_seconds: int = 21600
    semaphore_image: str = "semaphoreui/semaphore:v2.19.12"
    caddy_image: str = "caddy:2.11.4"
    aio_image: str = "ghcr.io/nextcloud-releases/all-in-one:latest"
    proxy_mode: str = "existing_host_proxy"

    def validate(self) -> "Config":
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise CloudOpsError("Unsupported configuration schema version.")
        if self.provider not in PROVIDERS:
            raise CloudOpsError("Unknown provider.")
        if not re.fullmatch(r"[a-z][a-z0-9-]{2,39}", self.instance_id):
            raise CloudOpsError("instance_id must be 3–40 lowercase letters, numbers or hyphens.")
        if self.mode not in ("primary", "recovery-test"):
            raise CloudOpsError("mode must be primary or recovery-test.")
        private_ipv4(self.management_ip)
        cloud_url(self.cloud_url)
        for name in ("management_port", "aio_admin_port"):
            value = getattr(self, name)
            if type(value) is not int or not 1024 <= value <= 65535:
                raise CloudOpsError(f"{name} must be between 1024 and 65535.")
        if len({self.management_port, self.aio_admin_port, 3000, 9080, 11000}) != 5:
            raise CloudOpsError("Management, AIO and reserved internal ports must be distinct.")
        for name in ("data_mount", "data_path", "backup_mount", "backup_path"):
            safe_path(getattr(self, name), name)
        dm, dp, bm, bp = map(PurePosixPath, (self.data_mount, self.data_path, self.backup_mount, self.backup_path))
        if not dp.is_relative_to(dm) or dp == dm or not bp.is_relative_to(bm) or bp == bm:
            raise CloudOpsError("Data and backup directories must be children of their required mounts.")
        if dm.is_relative_to(bm) or bm.is_relative_to(dm):
            raise CloudOpsError("Data and backup mounts must be separate, non-nested paths.")
        for name in ("data_identity", "backup_identity"):
            identity = getattr(self, name)
            if not isinstance(identity, dict) or set(identity) - {"uuid", "source", "fstype"}:
                raise CloudOpsError(f"Invalid {name}.")
            if any(not isinstance(v, str) or len(v) > 4096 for v in identity.values()):
                raise CloudOpsError(f"Invalid {name} fields.")
        if type(self.minimum_free_gib) is not int or not 1 <= self.minimum_free_gib <= 100000:
            raise CloudOpsError("minimum_free_gib must be a positive whole number.")
        if type(self.job_timeout_seconds) is not int or not 300 <= self.job_timeout_seconds <= 86400:
            raise CloudOpsError("job_timeout_seconds must be between 300 and 86400.")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
            raise CloudOpsError("Use a valid timezone such as America/Denver.") from exc
        if self.proxy_mode != "existing_host_proxy":
            raise CloudOpsError("This pilot supports an existing host-side HTTPS proxy or Tailscale Serve only.")
        expected = {"semaphore_image": "semaphoreui/semaphore:", "caddy_image": "caddy:", "aio_image": "ghcr.io/nextcloud-releases/all-in-one:"}
        for name, prefix in expected.items():
            val = getattr(self, name)
            if not isinstance(val, str) or not val.startswith(prefix) or not re.fullmatch(r"[a-zA-Z0-9./:@_-]+", val):
                raise CloudOpsError(f"{name} must reference its approved upstream repository.")
        return self

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        if not isinstance(data, dict):
            raise CloudOpsError("Configuration must be a JSON object.")
        try:
            return cls(**data).validate()
        except TypeError as exc:
            raise CloudOpsError("Unknown or invalid configuration fields.") from exc

    @classmethod
    def load(cls, path: Path) -> "Config":
        try:
            return cls.from_dict(json.loads(path.read_text()))
        except (OSError, ValueError) as exc:
            raise CloudOpsError(f"Cannot read configuration: {path}") from exc
