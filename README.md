# Homelab CloudOps

[![CI](https://github.com/wesleyhawes/homelab-cloudops/actions/workflows/ci.yml/badge.svg)](https://github.com/wesleyhawes/homelab-cloudops/actions/workflows/ci.yml)

**Release 0.1.0a1 · Engineering pilot · September 28, 2026**

A standalone, Docker Compose-based personal-cloud manager with local Ansible playbooks and a mobile-friendly browser console. No Git server, Git account, repository checkout, CI pipeline, external identity provider or Kubernetes cluster is required to operate it.

**Do not place irreplaceable files in this pilot until the real-host acceptance tests in `docs/ACCEPTANCE.md` pass on your equipment.** This package was not deployed to a real homelab during development. Local automated tests are evidence about the code, not proof that Docker, Semaphore, AIO or disaster recovery work end to end on your server. See `validation/` for the exact results and limitations.

## Start here

Download the source with GitHub's **Code → Download ZIP**, or clone it:

```bash
git clone https://github.com/wesleyhawes/homelab-cloudops.git
cd homelab-cloudops
```

The goal is an appliance-like experience: install on a dedicated homelab server,
then manage the cloud from a browser. This pilot starts with Nextcloud AIO;
the other provider entries are planned, disabled adapters.

Read **[START_HERE.md](START_HERE.md)**. For a safe, simulated desktop preview without Docker or root privileges:

```bash
python3 tools/preview.py
```

Open `http://127.0.0.1:8765/cloudops/` on that computer. The preview has a prominent simulation banner. Its actions never SSH to a host or deploy an application. Do not enter real credentials.

On a **dedicated Ubuntu Server 24.04 x86-64 test VM/host**, after preparing the required storage and application HTTPS routing:

```bash
sudo bash install.sh
```

The installer asks questions in the terminal. Normal operations are browser-managed after bootstrap. The first version does **not** yet provide a complete browser-based installation wizard.

## What is implemented

| Component | Implementation |
|---|---|
| Git-free installation | Local package bootstrap, guided terminal configuration, official Docker Engine installation when absent, Compose generation. |
| Management runtime | Semaphore with SQLite, Caddy private HTTPS, prepackaged local Ansible launchers; no Git checkout. |
| Mobile/laptop console | Responsive status cards, approval dialogs, task history, streamed output and native Semaphore session integration. |
| Persistent operations | Host-side SQLite job admission and systemd services independent of browser connection lifetime. |
| Initial provider | Nextcloud AIO mastercontainer deployment with native application/container ownership preserved. |
| Backup operations | Native AIO backup and integrity checking with fresh completion/archive evidence checks. |
| Storage protections | Exact mount enrollment, identity validation, free-space checks, symlink rejection and a Docker startup mount guard. |
| Recovery assistance | Non-secret recovery kit, guided native AIO restoration, optional seeded WebDAV probe on a distinct recovery-test host. |
| Future providers | Explicit, disabled registry entries and role stubs for ownCloud Infinite Scale, ownCloud Server and OxiCloud. |

The mobile console is a small static interface in front of Semaphore's existing API. It does not invent a second authentication database or task scheduler. Application users, files and shares remain in Nextcloud's own interface.

## Important boundaries

* This pilot accepts only a dedicated Ubuntu 24.04 x86-64 systemd host with Docker Engine/Compose. Fedora, ARM64, Podman and Kubernetes are not qualified.
* The data directory must live on a separate, already mounted ext4/XFS filesystem. The backup destination must be on a different mounted filesystem. A second partition on the same physical disk still is not independent disaster protection.
* The installer configures **Docker's service-wide startup dependency** on the data mount. Do not run it directly on a shared Docker host such as an existing multipurpose AI server.
* An existing AIO installation is not automatically adopted. Provider or data-path changes are not treated as harmless redeploys.
* A real application hostname and correctly trusted HTTPS route to the host's `127.0.0.1:11000` are prerequisites. The initial wizard does not manage domain registration, DNS-provider credentials or router forwarding.
* Complete initial AIO setup and the first native backup through the supported AIO interface. CloudOps uses no undocumented write APIs to bypass onboarding.
* Automated application upgrades, destructive one-click restores, manager self-updates and automatic migration between providers are **not implemented**. Native AIO updates/restores are guided in the runbooks.
* The backup adapter supports a mounted local backup path, which may be an appropriate NAS mount. AIO remote-Borg endpoints are not qualified in this adapter.
* The recovery probe checks one dedicated account, one seeded file and anonymous denial. It is not full-corpus, all-permissions, share-link or application-ecosystem verification.
* Real mobile Safari/Android Chrome, native Semaphore authentication/SSH/container integration, reboot guards and separate-host restoration still require field validation.

## Command surface

```text
cloudctl providers
cloudctl validate reviewed-config.json
cloudctl render reviewed-config.json --output preview/
sudo cloudctl run check
sudo cloudctl run deploy
sudo cloudctl run backup
sudo cloudctl run backup_check
sudo cloudctl run verify
sudo cloudctl run recovery_info
sudo cloudctl run verify_recovery
sudo cloudctl history
sudo cloudctl follow <host-job-id>
sudo cloudctl probe-credentials
sudo cloudctl probe-enroll
sudo cloudctl export-recovery /root/cloudops-recovery-kit.tar.gz
sudo cloudctl manager-backup /root/cloudops-manager-snapshot.tar.gz
sudo cloudctl enable-backup-timer
```

Maintenance commands run an allowlisted operation. They do not accept arbitrary shell commands, playbooks or Docker arguments from the browser. `cloudctl acknowledge <job-id>` is a root-only recovery action after inspecting an interrupted job; it does not mark failure as success.

## Project map

```text
install.sh                     Explicit, first-run Linux bootstrap
src/cloudops/                  Config, lifecycle, storage, evidence, jobs and CLI
src/cloudops/providers/         Provider registry, protocol and AIO adapter
ansible/                       Host-side provider lifecycle playbooks and roles
semaphore/                     Local launcher playbooks and restricted SSH bridge
web/                           Responsive browser interface and short user guide
examples/                      Configuration and rendered Compose previews
catalog/                       Version/baseline metadata and qualification status
docs/                          Installation, access, operations, recovery, security
integrations/                  Optional Git-platform integration notes
prompts/                       Follow-on implementation and qualification brief
tests/                         Unit and contract tests
tools/                         Safe preview and validation scripts
validation/                    Actual local reports and labeled preview images
```

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
make test
make validate
```

For network-backed browser smoke tests on a development machine that permits loopback browser navigation: `pip install -e '.[browser-test]'`, install the appropriate Playwright Chromium runtime, then `make browser-test`. `CHROMIUM_PATH` may select an existing Chromium executable. The development artifact also includes an in-memory rendering test for restricted environments. Neither test mode accesses a real server.

GitHub Actions runs unit tests, source checks, Ansible syntax checks, Compose
validation, browser smoke tests and a Python package build on pushes to `main`
and pull requests. See [CI details](docs/CI.md) for cost, scope and local commands,
and [CONTRIBUTING.md](CONTRIBUTING.md) for the path toward an appliance release.

Track the implementation work in [PRIORITIES.md](PRIORITIES.md). An hourly private
Gitea backup runs equivalent checks and delivers complete source packages;
see [Gitea backup and CI/CD](docs/GITEA.md). GitHub `main` requires a pull request
and passing CI.

Dependency resolution currently uses PyPI and upstream container registries. Image tags are selected deliberately and resolved image IDs/digests are recorded at install time; this is **not yet a hermetic, hash-locked or signed release**. AIO's `latest` master image is its upstream-managed channel, not a promise that every child image is frozen. Do not introduce a competing container updater.

Original project code is provided under the MIT license. Upstream products retain their own licenses and trademarks; their images are downloaded separately, not redistributed in this archive. See `NOTICE.md` and `docs/SOURCES.md`.
