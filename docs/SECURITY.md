# Security model and limitations

This is a single-owner engineering pilot, not a security-audited appliance or multi-tenant service. Test with disposable data. The code contains explicit safeguards, but live authentication, firewall, privileged-execution and restore behavior still require integration testing.

## Trust boundaries

The owner, host root, released playbooks and AIO are trusted. Semaphore can request powerful fixed host operations but receives no Docker socket, general-purpose root SSH key or user-supplied shell execution path. The bridge SSH public key has `restrict` and a forced command; the gateway accepts only an exact operation name; sudo permits exact script/argument combinations. Host-key checking is enabled explicitly even if the container's SSH defaults are permissive.

The root-owned source and host executable paths are not writable by the bridge account. The root installer must not be run on unreviewed code. A malicious release can execute as root; a SHA-256 manifest protects transfer integrity only, not publisher identity or authenticity. Signed releases and a complete dependency lock are future work.

AIO's Docker socket mount is required by its deployment model. A `:ro` socket bind does not make Docker daemon API requests read-only; treat AIO as host-privileged.

## Management authentication

Use Semaphore's native owner login and enable TOTP, saving recovery codes outside the application. Ordinary family file users should not receive management access. Native project-level task permissions remain the enforcement boundary; portal button visibility is not access control.

The portal uses same-origin native API calls. Caddy adds a cross-site mutation rejection based on Fetch Metadata, security headers and a restrictive policy for the static portal. These are defense-in-depth, not a complete authentication/CSRF security review. Additional reverse-proxy origins, cookies, TOTP and recovery flows must be validated on a real deployment.

There is no built-in public login or unauthenticated remote shell API. Do not place management behind public tunnels or expose it through router forwarding. Restrict SSH access by network policy as appropriate, including the manager-to-host bridge path.

## Secrets and logs

Secrets are generated during setup and retained on rerun. Host parent directories are root-only. Individual read-only bind-mounted files are readable by the manager container's user; the bridge copies its key to a private temporary file before SSH so OpenSSH does not reject overly permissive key-file modes. This is deliberate file-permission handling, not encryption at rest.

Compose secrets are file mounts, not a vault. Protect host disks, backup archives and operator devices. The AIO administrator passphrase, cloud admin account, Semaphore owner, Borg passphrase and probe app password are separate credentials. Do not conflate them or save all of them only inside the cloud.

Do not upload root job logs or application logs without reviewing/redacting them. The project avoids exposing known credentials in its own result fields and command-line arguments, but it does not claim all upstream diagnostic output is free of personal metadata. `manager-backup` contains sensitive keys and configuration in a root-only plaintext archive until you encrypt/protect it separately.

## Storage and failure safety

The installer never formats disks, removes persistent volumes, runs a global Docker prune or adopts an existing unowned AIO. Required mounts are enrolled by UUID when available or source/fstype otherwise. Symlink storage paths, mismatched identity, insufficient capacity and conflicting application state fail closed.

The Docker daemon startup guard affects all containers on the dedicated host. It can make the browser unavailable precisely when storage needs repair. Preserve SSH/local-console access. It does not detect every possible device fault or guarantee protection against all kernel/filesystem failures.

## Provider and task safety

Planned providers fail before deployment and have no callable capabilities. User configuration cannot import arbitrary Python modules or select arbitrary playbooks. Host operations serialize, preserve durable IDs, and block later mutations after interrupted/failed work. No automatic migration rollback, native lock deletion or destructive restore is attempted.

Root administrators and the AIO native interface can bypass project-level coordination. Use one active maintenance authority. A preflight idle check cannot eliminate every race with an independently operated native interface.

## Exposure and threat testing still needed

Before a general release, verify real browser/TOTP/cookie behavior, cross-origin requests, native API authorization, injection and SSH forwarding denials, firewall reachability, mount loss and reboot behavior, recovery isolation, secret disclosure paths, upstream-image provenance and dependency vulnerabilities. See `ACCEPTANCE.md`. Report issues privately through your chosen project-maintainer channel; this archive does not configure or invent a reporting inbox.
