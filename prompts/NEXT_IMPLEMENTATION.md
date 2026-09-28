# Follow-on engineering brief

Work in this repository. Do not replace it with a generic installer or make Git a runtime prerequisite. Its user is a homelab owner who should manage normal operations from a phone or laptop without learning Ansible.

First read README.md, docs/ARCHITECTURE.md, docs/SECURITY.md, docs/PROVIDER_CONTRACT.md and docs/ACCEPTANCE.md. The existing 0.1.0a1 implementation is an unqualified engineering pilot: local mock/unit tests passed only as recorded in validation. Do not describe live deployment, restoration or security properties as proven until tested.

Prioritize a clean Ubuntu 24.04 x86-64 VM run of the complete Nextcloud AIO vertical slice. Validate the exact Semaphore image/API schema, SQLite secret configuration, local repository handling, native login/TOTP, custom launcher action plugin, forced-command SSH/sudo boundaries, host systemd job persistence and root Ansible lifecycle. Verify actual Docker Compose behavior and expected AIO state paths. Fix integration defects and add regression tests. Never disable SELinux globally or turn off certificate verification to get a green result.

Test first-run native onboarding, exact mounted data and backup paths, first native backup, CloudOps fresh-backup evidence, closing a mobile tab during work, reconnecting to the same task, reboot and missing-mount failure behavior, interruption handling and a distinct isolated recovery host with the original probe. Treat one-file verification as a scoped probe, not proof of every file/share. Produce a timestamped acceptance record with commands, versions/digests and results; do not fabricate missing runs.

Keep AIO in charge of its own child containers and application updates. Do not implement rollback by downgrading an image after migrations. Do not expose destructive restoration or arbitrary shell/playbook inputs to the browser. Keep root host code immutable to the manager and preserve native management access as a documented high-trust interface.

Then improve beginner onboarding and private HTTPS/access setup, browser reliability, notifications and manager recovery. Only after qualification, implement ownCloud Infinite Scale as its own adapter, classic ownCloud as a separate adapter, and OxiCloud initially experimental. Update strict schemas, registry, factory, approved Ansible role allowlist, provider-specific rendering/probes and capability-derived browser operations together. Never migrate providers by reusing an incompatible data directory or swapping image names.

Deliver tested increments, maintain an honest implemented/planned/validated matrix, and keep GitLab/Gitea/GitHub pipelines optional consumers of the same lifecycle engine.
