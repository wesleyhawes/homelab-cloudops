# Validation record — 0.1.0a1

**Scope: local development validation, not a live homelab qualification.**

| Check | Actual result |
|---|---|
| Unit, contract and rejected-command process tests | **147 passed** in the recorded final run. |
| Python compilation | Passed. |
| YAML parsing | Passed for 20 packaged YAML files. |
| Installer Bash syntax | Passed. |
| Browser JavaScript syntax | Passed with Node. |
| Chromium UI rendering/action checks | **10 passed**, with an in-memory simulated API and storage. |
| Desktop layout | Tested at 1440 px; no horizontal overflow. |
| Mobile layout | Tested at 390 px; no horizontal overflow. Not an actual phone test. |
| Network-backed browser smoke test | Not completed: the development environment blocks browser URL navigation. No browser policy was changed. A runnable test is included for a normal development laptop. |
| Docker Compose / native Semaphore / SSH / Ansible integration | **Not run.** Docker and ansible-playbook executables were absent from this development runtime. |
| Live Nextcloud onboarding, backup and integrity operations | **Not run.** |
| Real browser-close/systemd persistence and reboot/missing-mount tests | **Not run.** Unit tests verify job admission/persistence logic, not actual systemd behavior. |
| Distinct-host application restore | **Not run.** |
| Security audit and real native login/TOTP/cookies | **Not performed.** |

The included screenshots are actual renders of the packaged interface with a prominent simulation banner. Their displayed health, backup and execution values are test fixtures, not evidence from a server.

The passing tests exercise configuration rejection, provider gating, mount identity/symlink/capacity checks, stale/wrong-mode/failed backup evidence, serialized job admission, attention-state blocking, duplicate-submission cooldown, safe Compose shapes, original-fixture recovery checks, TLS destination pinning, API provisioning behavior under mocks, rejected SSH gateway arguments and UI confirmation/output rendering.

`local-checks.json` and `browser-checks.json` contain machine-readable outcomes. The local report's `success` field refers to the checks that were run; it does not mean skipped integration tests passed. The test environment used Python 3.13.5; the intended Ubuntu 24.04 host uses its supported Python environment and still needs qualification.

Run `docs/ACCEPTANCE.md` on a disposable dedicated Ubuntu 24.04 x86-64 VM before changing provider readiness from pilot to supported. Keep actual image versions/digests and a recovery transcript with that report. None of the checks accessed the user's homelab, Git accounts or real cloud data.
