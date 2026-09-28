"""JSON is valid YAML. Structured generation avoids interpolation injection."""
from pathlib import Path
from .config import Config
from .providers import provider_spec
from .util import atomic_json


def aio_compose(c: Config) -> dict:
    provider_spec(c.provider, "deploy")
    return {
        "name": "nextcloud-aio",
        "services": {"nextcloud-aio-mastercontainer": {
            "image": c.aio_image, "container_name": "nextcloud-aio-mastercontainer",
            "init": True, "restart": "always", "network_mode": "bridge",
            "ports": [f"{c.management_ip}:{c.aio_admin_port}:8080"],
            "environment": {"APACHE_PORT": "11000", "APACHE_IP_BINDING": "127.0.0.1",
                "NEXTCLOUD_DATADIR": c.data_path, "SKIP_DOMAIN_VALIDATION": "false"},
            "volumes": ["nextcloud_aio_mastercontainer:/mnt/docker-aio-config", "/var/run/docker.sock:/var/run/docker.sock:ro"],
        }},
        "volumes": {"nextcloud_aio_mastercontainer": {"name": "nextcloud_aio_mastercontainer"}},
    }


def manager_compose(c: Config, release: str = "/opt/cloudops/current") -> dict:
    return {
        "name": "cloudops-manager",
        "services": {
            "semaphore": {
                "image": c.semaphore_image, "restart": "unless-stopped",
                "ports": ["127.0.0.1:3000:3000"],
                "extra_hosts": ["cloudops-host:host-gateway"],
                "environment": {
                    "SEMAPHORE_DB_DIALECT": "sqlite", "SEMAPHORE_DB": "/var/lib/semaphore/cloudops.sqlite",
                    "SEMAPHORE_ADMIN": "admin", "SEMAPHORE_ADMIN_NAME": "CloudOps Owner",
                    "SEMAPHORE_ADMIN_EMAIL": "owner@localhost", "SEMAPHORE_ADMIN_PASSWORD_FILE": "/run/secrets/admin_password",
                    "SEMAPHORE_ACCESS_KEY_ENCRYPTION_FILE": "/run/secrets/access_key",
                    "SEMAPHORE_WEB_HOST": f"https://{c.management_ip}:{c.management_port}",
                    "SEMAPHORE_PLAYBOOK_PATH": "/tmp/semaphore", "TZ": c.timezone,
                    "ANSIBLE_HOST_KEY_CHECKING": "True",
                    "ANSIBLE_CONFIG": "/opt/cloudops-playbooks/ansible.cfg",
                },
                "volumes": ["semaphore_data:/var/lib/semaphore", "semaphore_config:/etc/semaphore",
                    f"{release}/semaphore:/opt/cloudops-playbooks:ro",
                    "/etc/cloudops/known_hosts:/opt/cloudops-known-hosts:ro"],
                "secrets": ["admin_password", "access_key", "bridge_key"],
                "security_opt": ["no-new-privileges:true"],
                "logging": {"driver": "json-file", "options": {"max-size": "10m", "max-file": "3"}},
            },
            "gateway": {
                "image": c.caddy_image, "restart": "unless-stopped", "network_mode": "host",
                "volumes": ["/etc/cloudops/Caddyfile:/etc/caddy/Caddyfile:ro", "caddy_data:/data", "caddy_config:/config",
                    f"{release}/web:/srv/cloudops:ro", "/etc/cloudops/public:/srv/cloudops-config:ro"],
                "security_opt": ["no-new-privileges:true"],
                "logging": {"driver": "json-file", "options": {"max-size": "10m", "max-file": "3"}},
            },
        },
        "volumes": {key: {} for key in ("semaphore_data", "semaphore_config", "caddy_data", "caddy_config")},
        "secrets": {key: {"file": f"/etc/cloudops/secrets/{key}"} for key in ("admin_password", "access_key", "bridge_key")},
    }


def caddyfile(c: Config) -> str:
    # Static portal deliberately uses the same origin and native Semaphore session.
    # No public mutation API or separate bearer token is introduced.
    return f"""{{
    admin off
    auto_https disable_redirects
}}
(cloudops_routes) {{
    @cross_origin {{
        path /api/*
        method POST PUT PATCH DELETE
        header Sec-Fetch-Site cross-site
    }}
    respond @cross_origin "Cross-origin operations are not allowed" 403
    header {{
        X-Content-Type-Options nosniff
        Referrer-Policy no-referrer
        X-Frame-Options DENY
        Cache-Control no-store
    }}
    redir /cloudops /cloudops/ 308
    # Mount the containing directory so atomic portal updates are visible.
    handle /cloudops/config.json {{
        root * /srv/cloudops-config
        rewrite * /portal.json
        file_server
    }}
    handle_path /cloudops/* {{
        root * /srv/cloudops
        header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        file_server
    }}
    handle {{
        reverse_proxy 127.0.0.1:3000
    }}
}}
https://{c.management_ip}:{c.management_port} {{
    bind {c.management_ip}
    tls internal
    import cloudops_routes
}}
# This loopback-only listener is for an existing trusted HTTPS proxy or Tailscale Serve.
http://:9080 {{
    bind 127.0.0.1
    import cloudops_routes
}}
"""


def render_all(c: Config, destination: Path) -> None:
    c.validate()
    destination.mkdir(parents=True, exist_ok=True)
    atomic_json(destination / "manager.compose.yaml", manager_compose(c))
    atomic_json(destination / "nextcloud.compose.yaml", aio_compose(c))
    (destination / "Caddyfile").write_text(caddyfile(c))
