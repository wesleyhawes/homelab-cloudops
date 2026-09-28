# Architecture and ownership

The normal operation path is:

```text
Phone or laptop browser
    |
    | private HTTPS / native Semaphore session
    v
Caddy ---- static /cloudops/ interface
    |
    v
Semaphore: SQLite task history + preconfigured local Ansible launchers
    |
    | pinned-host-key SSH, forced exact operation, no arbitrary arguments
    v
cloudops-bridge host account
    |
    | exact sudo command allowlist
    v
cloudctl -> SQLite admission -> independent systemd job
    |
    v
root-owned local Ansible playbook -> provider adapter
    |
    v
Docker Compose / supported native AIO operations
    |
    v
AIO-owned application containers + enrolled persistent storage
```

## Two execution contexts, one lifecycle implementation

Semaphore runs a **launcher** playbook inside its container. Its localhost is not the Docker host. A custom action plugin streams the fixed SSH bridge output back into the existing task history. Host-side Ansible performs the actual operation using root-owned code. The Python adapter implements details such as evidence parsing, storage checks and protected state that are more directly unit-testable than shell fragments.

The host systemd service owns the operation lifetime. A browser tab can disappear without terminating the host operation. If the entire Semaphore container dies, its task may fail even while the independent host job continues; use `cloudctl history/follow` before retrying. Automatic reconciliation of a failed console task with a still-running host job is not implemented in this first release.

## Ownership rules

* Compose manages the management project and the AIO **mastercontainer**.
* AIO manages its own child containers, database lifecycle and native backup/restore implementation.
* Ansible manages host configuration, enrollment, preflight and lifecycle invocation; it does not independently recreate AIO's database or child images.
* One instance is permitted per dedicated host. Fixed upstream AIO names are intentional.
* Git adapters, when added, call the same admitted operations and never become the scheduler of record for backups.

## Files and state

| Path | Purpose |
|---|---|
| `/opt/cloudops/releases/0.1.0a1` | Root-owned release code. |
| `/opt/cloudops/current` | Root-owned symlink to the selected release. |
| `/opt/cloudops/venv` | Host CLI and Ansible environment. |
| `/etc/cloudops/config.json` | Strict, root-only configuration and enrolled mount identities. |
| `/etc/cloudops/secrets` | Root-only parent directory; individual bind-mounted secret files have readable container permissions. |
| `/etc/cloudops/manager.compose.yaml` | Manager desired configuration. |
| `/etc/cloudops/nextcloud.compose.yaml` | AIO master configuration. |
| `/etc/cloudops/public/portal.json` | Non-secret identifiers and operation metadata visible to the static interface. |
| `/var/lib/cloudops/jobs.sqlite` | Durable host job admission/history. |
| `/var/lib/cloudops/jobs/<id>/` | Root-only per-operation output and structured result. |
| `/var/lib/cloudops/last-*.json` | Evidence from actual successful operations on this host. |
| Docker named manager volumes | Semaphore SQLite/config and Caddy CA/config state. |
| Required data/backup mounts | User cloud data and Borg backup repository. |

## State machine

```text
queued -> running -> success
                  -> failed       (read-only operation)
                  -> attention    (mutation; future mutations blocked)
attention -> acknowledged         (explicit root inspection; not success)
```

A unique SQLite index plus transactional admission prevents multiple CloudOps mutations. A host file lock also serializes actual execution. AIO's current Borg/update state and native lock file are inspected. These defenses cannot prevent a trusted root operator from bypassing them or manually starting native work immediately after a check; maintenance policy still requires one active authority.

The worker never automatically replays a job after a host restart. A queued/running record left by a crash must be inspected and acknowledged explicitly. Timeouts stop observation and move a mutation to attention; native AIO work may still be running. There is no browser cancellation button for migrations.

## Frontend

The interface is static HTML, CSS and JavaScript. It uses same-origin native Semaphore authentication; it does not store API tokens. Browser local storage contains only the selected non-secret task ID. Task output is rendered using `textContent`, not `innerHTML`. Stored job markers transport non-secret structured status. Overview data carries a check timestamp and warns when old.

The interface is not a full observability platform, a Kubernetes dashboard, a replacement file browser or an authority for every application setting. The application, AIO native admin page and advanced Semaphore interface remain accessible through explicit links.

## Network and privilege boundary

Neither the static web server nor Semaphore receives the Docker socket. The bridge key can request only seven exact operations, using host-key checking and disabled SSH forwarding. The key grants **powerful fixed maintenance capabilities**, not a generally unprivileged role.

AIO itself retains Docker socket access required by its design. A read-only filesystem mount of the socket does not make the Docker API read-only. Host root and AIO are high-trust components. This is not a hardened multi-tenant service.
