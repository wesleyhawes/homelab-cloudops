"""Guided host preparation after the explicit package bootstrap."""
from __future__ import annotations
import argparse
import base64
import dataclasses
import json
import os
import secrets
import shutil
import socket
import sys
import time
from pathlib import Path
from . import paths
from .config import Config
from .errors import CloudOpsError
from .render import manager_compose, caddyfile
from .storage import mount_identity, check_storage
from .util import atomic_json, require_root, run
from .semaphore_api import SemaphoreAPI, provision


def ask(label: str, default: str) -> str:
    return input(f"{label} [{default}]: ").strip() or default


def writable_file(path: Path, content: str, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != content:
        path.write_text(content)
    path.chmod(mode)


def wizard() -> Config:
    print("\nChoose existing mounted storage. This installer never creates partitions or formats disks.")
    run_result = run(["findmnt", "--real", "--output", "TARGET,SOURCE,FSTYPE"], check=False)
    print(run_result.stdout)
    data_mount = ask("Data disk mountpoint", "/srv/cloud-data")
    backup_mount = ask("Separate backup disk/NAS mountpoint", "/srv/cloud-backup")
    config = Config(
        instance_id=ask("Name for this cloud", "personal-cloud"),
        management_ip=ask("Server's private IPv4 address (127.0.0.1 is local-only)", "127.0.0.1"),
        cloud_url=ask("HTTPS application hostname (your proxy must route to this server's 127.0.0.1:11000)", "https://cloud.example.com"),
        data_mount=data_mount, data_path=data_mount + "/nextcloud", backup_mount=backup_mount,
        backup_path=backup_mount + "/aio", timezone=ask("Timezone", "UTC"),
        mode=ask("Install mode: primary or recovery-test", "primary"),
        data_identity=mount_identity(data_mount), backup_identity=mount_identity(backup_mount),
    ).validate()
    if config.cloud_url == "https://cloud.example.com":
        raise CloudOpsError("Replace the example hostname with the actual DNS/Tailscale hostname before installing.")
    return config


def ensure_secret(name: str, content: str):
    folder = Path("/etc/cloudops/secrets")
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder.chmod(0o700)
    path = folder / name
    if not path.exists():
        path.write_text(content + "\n")
    # Host ancestors are root-only. Bind-mounted individual files must be readable by UID 1001.
    # The bridge copies its mounted key to a private 0600 temporary file before invoking SSH.
    path.chmod(0o444)


def ensure_ssh_bridge():
    run(["systemctl", "enable", "--now", "ssh"])
    if run(["id", "cloudops-bridge"], check=False).returncode:
        run(["useradd", "--system", "--home-dir", "/var/lib/cloudops-bridge", "--shell", "/bin/sh", "cloudops-bridge"])
    run(["usermod", "--password", "*", "cloudops-bridge"])
    home = Path("/var/lib/cloudops-bridge")
    (home / ".ssh").mkdir(parents=True, exist_ok=True)
    home.chmod(0o755)
    (home / ".ssh").chmod(0o755)
    key = Path("/etc/cloudops/secrets/bridge_key")
    if not key.exists():
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "cloudops-fixed-operations", "-f", str(key)])
    key.chmod(0o444)
    pub = Path(str(key) + ".pub").read_text().strip()
    forced = 'restrict,command="/usr/local/libexec/cloudops-ssh-gateway" ' + pub + "\n"
    writable_file(home / ".ssh/authorized_keys", forced)
    gateway = Path("/usr/local/libexec/cloudops-ssh-gateway")
    gateway.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(paths.RELEASE / "bin/cloudops-ssh-gateway", gateway)
    gateway.chmod(0o755)
    host_pub = Path("/etc/ssh/ssh_host_ed25519_key.pub").read_text().split()
    writable_file(Path("/etc/cloudops/known_hosts"), f"cloudops-host {host_pub[0]} {host_pub[1]}\n")
    allowed = ["check", "deploy", "backup", "backup_check", "verify", "recovery_info", "verify_recovery"]
    commands = ", ".join("/opt/cloudops/current/bin/cloudops-host " + item for item in allowed)
    sudoers = Path("/etc/sudoers.d/cloudops-bridge")
    writable_file(sudoers, "cloudops-bridge ALL=(root) NOPASSWD: " + commands + "\n", mode=0o440)
    run(["visudo", "-cf", str(sudoers)])


def ensure_storage_guard(c: Config):
    unit = run(["systemd-escape", "--path", "--suffix=mount", c.data_mount]).stdout.strip()
    content = f"""[Unit]
RequiresMountsFor={c.data_mount}
BindsTo={unit}
After={unit}
[Service]
ExecStartPre=/opt/cloudops/venv/bin/python -I -m cloudops.cli guard-storage
"""
    writable_file(Path("/etc/systemd/system/docker.service.d/30-cloudops-storage.conf"), content)
    # Do not restart Docker here; direct preflight already protects this installation.
    # On subsequent daemon starts, mount identity is checked before any auto-restarting child containers.
    run(["systemctl", "daemon-reload"])


def ensure_backup_units(c: Config):
    writable_file(Path("/etc/systemd/system/cloudops-backup.service"), """[Unit]
Description=CloudOps verified native backup
After=docker.service
Requires=docker.service
[Service]
Type=oneshot
UMask=0077
ExecStart=/opt/cloudops/venv/bin/python -I -m cloudops.cli run backup
TimeoutStartSec=infinity
""")
    writable_file(Path("/etc/systemd/system/cloudops-backup.timer"), f"""[Unit]
Description=Daily CloudOps backup (explicitly enabled after a verified first backup)
[Timer]
OnCalendar=*-*-* 03:00:00 {c.timezone}
Persistent=true
RandomizedDelaySec=300
[Install]
WantedBy=timers.target
""")
    run(["systemctl", "daemon-reload"])


def free_ports(c: Config):
    for address, port in [(c.management_ip, c.management_port), ("127.0.0.1", 3000), ("127.0.0.1",9080), (c.management_ip,c.aio_admin_port), ("127.0.0.1",11000)]:
        with socket.socket() as sock:
            try:
                sock.bind((address, port))
            except OSError as exc:
                raise CloudOpsError(f"Address/port unavailable: {address}:{port}. Resolve existing services or select the correct server address.") from exc


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, help="Use reviewed JSON instead of terminal questions; missing mount identities are enrolled locally")
    args = parser.parse_args(argv)
    require_root()
    os.umask(0o077)
    Path("/etc/cloudops").mkdir(parents=True, exist_ok=True, mode=0o755)
    if paths.CONFIG.exists():
        config = Config.load(paths.CONFIG)
        print("Existing configuration retained; credentials and storage choices will not be regenerated.")
    else:
        if args.config:
            config = Config.load(args.config)
            config = dataclasses.replace(config, data_identity=mount_identity(config.data_mount) if not config.data_identity else config.data_identity,
                                         backup_identity=mount_identity(config.backup_mount) if not config.backup_identity else config.backup_identity)
        else:
            config = wizard()
        from .providers import provider_spec
        provider_spec(config.provider)
        if config.cloud_url == "https://cloud.example.com":
            raise CloudOpsError("An actual application hostname is required.")
        check_storage(config, backup=True)
        free_ports(config)
        atomic_json(paths.CONFIG, config.to_dict())
    check_storage(config, backup=True)
    Path(config.backup_path).mkdir(parents=True, exist_ok=True, mode=0o750)
    ensure_secret("admin_password", secrets.token_urlsafe(24))
    ensure_secret("access_key", base64.b64encode(secrets.token_bytes(32)).decode())
    ensure_ssh_bridge()
    ensure_storage_guard(config)
    ensure_backup_units(config)
    atomic_json(Path("/etc/cloudops/manager.compose.yaml"), manager_compose(config))
    writable_file(Path("/etc/cloudops/Caddyfile"), caddyfile(config))
    portal = Path("/etc/cloudops/public/portal.json")
    portal.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    portal.parent.chmod(0o755)
    if not portal.exists():
        atomic_json(portal, {"status": "provisioning"}, mode=0o644)
    compose = ["docker", "compose", "-f", "/etc/cloudops/manager.compose.yaml"]
    run(compose + ["config", "--quiet"])
    print("Pulling approved management images. Initial installation needs internet access.")
    # Show progress; these commands contain no credentials in arguments.
    import subprocess
    subprocess.run(compose + ["pull"], check=True)
    subprocess.run(compose + ["up", "-d"], check=True)
    # Capture actual image IDs/digests; no claim that tags alone are immutable.
    observed = {}
    for name, image in (("semaphore", config.semaphore_image), ("caddy", config.caddy_image)):
        value = json.loads(run(["docker", "image", "inspect", image]).stdout)[0]
        observed[name] = {"requested": image, "image_id": value["Id"], "repo_digests": value.get("RepoDigests", [])}
    atomic_json(paths.STATE / "management-images.json", observed)
    api = SemaphoreAPI()
    password = Path("/etc/cloudops/secrets/admin_password").read_text().strip()
    for attempt in range(90):
        try:
            api.login(password)
            break
        except CloudOpsError:
            time.sleep(2)
    else:
        raise CloudOpsError("Semaphore did not become ready. Inspect: docker compose -f /etc/cloudops/manager.compose.yaml logs semaphore")
    provision(api, config, portal)
    ca = Path("/root/cloudops-management-ca.crt")
    proc = run(compose + ["exec", "-T", "gateway", "cat", "/data/caddy/pki/authorities/local/root.crt"], check=False)
    if proc.returncode == 0 and "BEGIN CERTIFICATE" in proc.stdout:
        writable_file(ca, proc.stdout)
    print(f"\nManagement: https://{config.management_ip}:{config.management_port}/cloudops/")
    print("Sign in through Semaphore, then return to /cloudops/. Administrator username: admin")
    print("Read the generated password locally with: sudo cat /etc/cloudops/secrets/admin_password")
    print("Enable TOTP in the Semaphore account settings before using remote management.")
    print("Trust /root/cloudops-management-ca.crt on your own devices, or use the documented trusted HTTPS/Tailscale proxy path.")
    print("The local AIO onboarding endpoint uses AIO's own self-signed certificate; see docs/ACCESS.md.")
    print("Next: select Install cloud in the browser; then complete AIO setup and its first backup.")
    print("No cloud application, backup or restore test is claimed complete by this manager installation.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CloudOpsError, OSError) as exc:
        print(f"CloudOps setup: {exc}", file=sys.stderr)
        raise SystemExit(1)
