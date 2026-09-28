# Gitea backup and CI/CD

GitHub is the canonical contribution repository. The private backup is
[`machine-rocinante-codex/github-wesleyhawes--homelab-cloudops`](https://gitea.dataprofusion.com/machine-rocinante-codex/github-wesleyhawes--homelab-cloudops)
on `gitea.dataprofusion.com`.

## Source backup

The `homelab-cloudops-gitea-backup.timer` user timer on Rocinante fetches public
GitHub branches/tags hourly, then pushes them to a normal private Gitea repository.
This uses the same approach as the existing portfolio backups. Gitea's native
pull-mirror queue did not process manual requests during setup, so the backup
does not depend on that queue or change the running Gitea service.

The [backup script](../integrations/gitea/backup.py) retains source-deleted refs
and archives both incoming and previous ref tips under `cloudops-backup/` tags
before updating changed refs with atomic, lease-protected pushes. Unknown
destination-only edits stop synchronization instead of being overwritten.
Every run verifies destination refs and writes a status report. The timer invokes
a separately installed copy of the script; source changes do not automatically
replace the installed backup program.

The backup contains Git branches, tags and their reachable history. It excludes
issues, PR metadata, release attachments, Actions history, local files and secrets.
Keep those in the relevant server backups, and protect Gitea's own storage with
independent retention.

Make changes through GitHub PRs. Do not independently edit the Gitea backup's
source branches. As the `codex` user on Rocinante:

```bash
systemctl --user start homelab-cloudops-gitea-backup.service
systemctl --user list-timers homelab-cloudops-gitea-backup.timer
journalctl --user -u homelab-cloudops-gitea-backup.service -n 20
cat ~/.local/state/homelab-cloudops-backup/latest.json
```

The configuration is in `~/.config/homelab-cloudops-backup/config.json`; the
installed script is in `~/.local/lib/homelab-cloudops-backup/backup.py`. GitHub
fetches need no credential; Gitea pushes use the existing machine SSH key and
strict host-key verification. Compare both `main` commit IDs when checking
replication. The service/timer templates are in `integrations/gitea/`.

A user with access can recover the source with:

```bash
git clone ssh://git@gitea.dataprofusion.com:2222/machine-rocinante-codex/github-wesleyhawes--homelab-cloudops.git
```

## Gitea Actions

The dedicated [Gitea workflow](../.gitea/workflows/ci.yml) takes precedence over
the GitHub workflow on Gitea. It targets the existing `ubuntu-latest` runner label
and runs on mirrored `main` updates, version tags, or manual dispatch. GitHub PRs
run on GitHub-hosted runners; the mirror does not import PR metadata or automatically
execute contribution branches on the homelab runner.

It runs the same Python tests, source checks, Ansible checks, Compose validation,
browser smoke tests and wheel checks as GitHub. Gitea-specific differences:

- Node 20 versions of checkout/setup-python are pinned for the existing runner.
- setup-python does not send a Gitea token to GitHub's download API.
- Compose is downloaded with its published checksum and used as a standalone
  configuration validator. A Docker daemon is not needed by the checks.
- The full committed source, including the installer, web UI and playbooks, is
  packaged with a SHA-256 checksum. Wheels alone do not include the appliance assets.
- Successful runs upload packages and reports to a Gitea artifact with seven-day
  retention, using the artifact v3 protocol supported by the current server and
  runner. The job downloads the artifact again and verifies the source checksum
  and installer/runtime assets before reporting success.

The server currently runs Gitea 1.25.3. Its `permissions`, `concurrency` and job
timeout behavior differs from GitHub; do not treat copied YAML as a privilege or
approval boundary. This workflow uses no added secrets or deployment identities.
It builds development deliverables and does not deploy a host or publish a qualified
release. Review runner isolation before allowing other sources to execute there.

Download a successful run's artifact from its **Actions** page, extract it, and
check the source bundle before transferring it to a dedicated test VM:

```bash
cd dist
sha256sum --check homelab-cloudops-source-*.tar.gz.sha256
tar -xzf homelab-cloudops-source-<commit>.tar.gz
```

Follow `START_HERE.md` from the extracted tree. Artifacts are temporary delivery
outputs; the repository mirror is the persistent source backup.

The [verification run](https://gitea.dataprofusion.com/machine-rocinante-codex/github-wesleyhawes--homelab-cloudops/actions/runs/3)
passed 150 unit/contract tests, 10 browser checks, Ansible/Compose checks, package
builds, and artifact upload/download/checksum validation on 2026-09-28. A separate
clone from the Gitea backup passed `git fsck --full` and a fresh checkout contained
the installer and runtime assets. These checks do not qualify live cloud recovery.

## GitHub main protection

`main` requires a PR, the **Validate pilot** check from GitHub Actions, a branch
up to date with `main`, resolved review conversations and linear history. Force
pushes and branch deletion are disabled, including for administrators. Squash or
rebase merge after CI passes. The approval count is zero while the project has
one maintainer; a second person's approval is not required to merge your own PR.

References: [Gitea 1.25 Actions differences](https://docs.gitea.com/1.25/usage/actions/comparison/),
[GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
