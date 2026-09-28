# Upstream references and version basis

Reviewed September 28, 2026. No upstream binaries/images are vendored in this archive. Links are implementation references, not a claim of endorsement or completed interoperability testing. Recheck them before updating dependencies; native AIO evidence formats and Semaphore APIs can change.

| Subject | Primary reference |
|---|---|
| AIO deployment/onboarding/backup | https://github.com/nextcloud/all-in-one |
| AIO official Compose definition | https://github.com/nextcloud/all-in-one/blob/main/compose.yaml |
| AIO reverse proxy | https://github.com/nextcloud/all-in-one/blob/main/reverse-proxy.md |
| AIO local instances | https://github.com/nextcloud/all-in-one/blob/main/local-instance.md |
| AIO external backup helper, inspected release | https://raw.githubusercontent.com/nextcloud/all-in-one/v14.1.1/Containers/mastercontainer/daily-backup.sh |
| Borg success/evidence logic, inspected release | https://raw.githubusercontent.com/nextcloud/all-in-one/v14.1.1/Containers/borgbackup/backupscript.sh |
| Borg mode/archive-list behavior, inspected release | https://raw.githubusercontent.com/nextcloud/all-in-one/v14.1.1/Containers/borgbackup/start.sh |
| Nextcloud upgrade/downgrade constraints | https://docs.nextcloud.com/server/latest/admin_manual/maintenance/upgrade.html |
| Semaphore Docker, SQLite and file secrets | https://semaphoreui.com/docs/admin-guide/installation/docker |
| Semaphore local playbook directories | https://semaphoreui.com/docs/user-guide/repositories |
| Semaphore versioned API | https://raw.githubusercontent.com/semaphoreui/semaphore/v2.19.12/api-docs.yml |
| Semaphore task templates | https://semaphoreui.com/docs/user-guide/task-templates |
| Semaphore user/team permissions | https://semaphoreui.com/docs/user-guide/team |
| Docker Ubuntu installation | https://docs.docker.com/engine/install/ubuntu/ |
| Docker daemon security | https://docs.docker.com/engine/security/ |
| Docker firewall behavior | https://docs.docker.com/engine/network/packet-filtering-firewalls/ |
| Compose secrets | https://docs.docker.com/compose/how-tos/use-secrets/ |
| Caddy internal TLS | https://caddyserver.com/docs/caddyfile/directives/tls |
| Caddy automatic HTTPS/trust | https://caddyserver.com/docs/automatic-https |
| Tailscale private Serve | https://tailscale.com/docs/reference/tailscale-cli/serve |
| Ansible core package | https://pypi.org/project/ansible-core/ |
| ownCloud Infinite Scale (future) | https://github.com/owncloud/ocis |
| ownCloud Server Docker (future) | https://doc.owncloud.com/server/next/admin_manual/installation/docker/ |
| OxiCloud current upstream (future) | https://github.com/AtalayaLabs/OxiCloud |

The project selects Semaphore `v2.19.12`, Caddy `2.11.4` and host `ansible-core==2.21.4`. AIO uses its documented upstream-managed master image channel; evidence logic was inspected against AIO `v14.1.1`. Recording these values is not a substitute for running integration tests on those exact artifacts and the actual resolved child versions.
