# GitHub Actions

For the private source mirror and its analogous delivery workflow, see
[Gitea backup and CI/CD](GITEA.md). The working backlog is [PRIORITIES.md](../PRIORITIES.md).

The [CI workflow](../.github/workflows/ci.yml) runs on pull requests, pushes to
`main`, and manual dispatch. It uses one standard `ubuntu-24.04` GitHub-hosted
runner, Python 3.12 (the reference Ubuntu platform's Python version), and a
15-minute timeout. New runs cancel older runs for the same branch or PR.

The checks cover:

- Python compilation, YAML parsing, installer/launcher shell syntax, JavaScript
  syntax, and the unit/contract tests.
- Ansible playbooks, the Semaphore action plugin's resolution, and every
  implemented Nextcloud role entry point through syntax checks only.
- Example Docker Compose configuration validation without starting containers.
- Chromium against the local simulated API, including session handoff, task
  submission, reload reconnection, output escaping, and desktop/mobile layouts.
- Wheel and source distribution builds, then CLI smoke tests from an independently
  installed wheel outside the checkout.

Actions are pinned to commit SHAs. Dependabot proposes monthly updates for
Actions and Python dependencies. The workflow has read-only repository permission,
does not persist checkout credentials, and needs no secrets or homelab access.
It uses `pull_request`, so contributions can be tested without privileged workflows.

## Cost

GitHub documents standard hosted runners as free for public repositories in its
[Actions billing guide](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
This workflow uses a standard runner, no paid services, no scheduled runs, and
no uploaded artifacts or dependency caches. Test reports appear in the run logs
and summary. There is no Actions storage retained by an artifact-upload step.

If the repository is made private later, hosted runs consume the owner's included
monthly allowance; configure an Actions budget that stops usage before paid
overages. See [GitHub's budget documentation](https://docs.github.com/en/billing/concepts/budgets-and-alerts).

## Run the same checks locally

Use Python 3.12, Node.js, Docker Compose v2 or newer, and a Git checkout. On
Ubuntu, Playwright's browser installation command also installs OS dependencies.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,automation,browser-test]' build==1.6.1
node --check web/app.js
sh -n bin/cloudops-host
python tools/validate.py --report local/ci/local-checks.json
bash tools/check-ansible.sh
docker compose -f examples/rendered/manager.compose.yaml config --quiet
docker compose -f examples/rendered/nextcloud.compose.yaml config --quiet
python -m playwright install --with-deps chromium
CLOUDOPS_VALIDATION_DIR=local/ci CHROMIUM_PATH=/nonexistent/cloudops-chromium \
  python tools/browser_smoke.py
python -m build --outdir local/ci/dist
```

Generated local reports and build outputs are ignored by Git. The workflow also
installs the built wheel into a fresh virtual environment and checks `cloudctl
--help` and `cloudctl providers`. The wheel packages the Python CLI; install the
appliance pilot from a complete source checkout/archive, which also contains the
web UI, Ansible assets and installer.

## What a green run establishes

The workflow validates code and simulated browser behavior. It does not run
`install.sh`, start a cloud server, exercise native Semaphore authentication, or
prove a usable backup or recovery. Those are the next development milestone:
complete [ACCEPTANCE.md](ACCEPTANCE.md) on a dedicated Ubuntu VM and a separate
restore VM, using disposable data.

The reports under `validation/` were supplied with the original archive and are
historical evidence. New CI reports go under `local/ci/` and appear in the GitHub
run summary. `validation/imported-archive-manifest.sha256` is the original file
manifest, applicable only to the unchanged extracted archive. The imported
`homelab-cloudops-0.1.0a1.tar.gz` had SHA-256:

```text
9a6f3d629e07d9ec603742d6ee2a12d0d6c955dc3a3c113b9d8e0a3ccdc8663d
```
