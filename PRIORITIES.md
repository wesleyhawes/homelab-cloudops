# Project priorities

Updated: 2026-09-28. Status: engineering pilot, not yet a qualified appliance.

Use this file as the working backlog. Keep IDs stable, link a PR or a sanitized
acceptance report when closing an item, and update it in the same PR as the work.
Passing CI does not close a real-host acceptance item. Detailed requirements are
in [ACCEPTANCE.md](docs/ACCEPTANCE.md) and [ROADMAP.md](docs/ROADMAP.md).

## Repository foundation

- [x] F-01: Publish the MIT-licensed source on `wesleyhawes/homelab-cloudops`.
- [x] F-02: Run Python, Ansible, Compose, browser and package checks in GitHub Actions.
- [x] F-03: Protect GitHub `main`: PRs, current passing CI, resolved conversations,
  linear history, and no force pushes/deletion; include administrators.
- [x] F-04: Create an hourly private GitHub-to-Gitea source backup with retained
  historical ref tips. See
  [backup operations](docs/GITEA.md).
- [ ] F-05: Verify Gitea CI and download/check the delivered source artifact.
- [ ] F-06: Rehearse recovering a clean checkout from Gitea, and document separate
  backup/retention for issues, release assets and the Gitea server itself.

## P0 — Qualify the existing Nextcloud path

These block describing this project as a reliable appliance.

| ID | Status | Work | Done when |
| --- | --- | --- | --- |
| P0-01 | Todo | Clean installation on a dedicated Ubuntu 24.04 x86-64 VM | H01–H05 pass; OS, dependency/image versions and installer transcript recorded. |
| P0-02 | Todo | Storage failure and reboot behavior | H06–H07 pass, including missing/wrong mounts and Docker's startup guard. |
| P0-03 | Todo | Native management and first cloud onboarding | H08–H12 pass with real Semaphore login/TOTP, trusted HTTPS, actual Nextcloud onboarding and browser disconnect/reconnect. |
| P0-04 | Todo | Backup success, failure and scheduling | H13–H17 and H21 pass; fresh Borg evidence verified and failures/concurrent operations handled; only one backup scheduler enabled. |
| P0-05 | Todo | Restore onto a distinct, isolated VM | H18–H20 pass with seeded files, login/shares/permissions and rejection of wrong recovery targets. |
| P0-06 | Todo | Update and manager recovery | H22–H23 pass using verified backups, retained configuration and encryption material. |
| P0-07 | Todo | Review real security boundaries | H25 pass with recorded authorization, cross-origin mutation, output handling, SSH and secret-path review. |

## P1 — Make the qualified path approachable

- [ ] P1-01: Run H24 with a new user; document every place expert help is required.
- [ ] P1-02: Design and implement authenticated browser onboarding for storage,
  hostname, private access and certificate choices, preserving installation guards.
- [ ] P1-03: Validate real iOS/Android browsers and unreliable network reconnects.
- [ ] P1-04: Add backup-age/storage alerts, notification setup and guided recovery.
- [ ] P1-05: Automate encrypted, off-host manager backups and interruption reconciliation.

## P2 — Ship a repeatable appliance release

- [ ] P2-01: Lock resolved Python dependencies and platform-specific image digests
  for components this project owns; document AIO's upstream-managed components.
- [ ] P2-02: Publish versioned source packages, checksums, provenance and release
  notes only after qualification; CI artifacts are development deliveries.
- [ ] P2-03: Build a reproducible VM image with tested install/update/recovery paths.
- [ ] P2-04: Add an explicit, reviewed deployment workflow after P0 qualification;
  keep deployment credentials separate from contribution checks.

## P3 — Expand after the first appliance path works

- [ ] P3-01: Implement and independently qualify ownCloud Infinite Scale.
- [ ] P3-02: Evaluate classic ownCloud and OxiCloud against actual demand.
- [ ] P3-03: Qualify Fedora/SELinux and ARM64 as separate platform profiles.
- [ ] P3-04: Add optional monitoring/platform integrations while keeping everyday
  operation and backups independent of Git services.
