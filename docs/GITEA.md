# Gitea backup and CI/CD

GitHub is the canonical contribution repository. The private backup is
[`machine-rocinante-codex/github-wesleyhawes--homelab-cloudops`](https://gitea.dataprofusion.com/machine-rocinante-codex/github-wesleyhawes--homelab-cloudops)
on `gitea.dataprofusion.com`.

## Source backup

Gitea pulls the public GitHub repository every hour without a GitHub credential.
The mirror contains Git branches, tags and their reachable history. Mirror pruning
is disabled so source-side ref deletion does not immediately remove backup refs.
It is a source mirror, not a versioned archive of issues, pull requests, release
attachments, Actions history, local files or secrets. Keep those in the relevant
server backups. A mirrored ref can still advance; protect the Gitea server's own
storage with independent backup retention.

Make changes through GitHub PRs. Do not push independently to the Gitea mirror.
Use the repository's **Settings → Mirror Settings → Synchronize Now** to request
an immediate pull after a merge; otherwise allow the hourly interval and queue.
Compare the latest commit on both `main` branches when checking replication.

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
  retention, using the artifact v3 protocol supported by Gitea 1.25.

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

## GitHub main protection

`main` requires a PR, the **Validate pilot** check from GitHub Actions, a branch
up to date with `main`, resolved review conversations and linear history. Force
pushes and branch deletion are disabled, including for administrators. Squash or
rebase merge after CI passes. The approval count is zero while the project has
one maintainer; a second person's approval is not required to merge your own PR.

References: [Gitea mirroring](https://docs.gitea.com/usage/repository/repo-mirror/),
[Gitea 1.25 Actions differences](https://docs.gitea.com/1.25/usage/actions/comparison/),
[GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
