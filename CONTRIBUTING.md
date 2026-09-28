# Contributing

Homelab CloudOps aims to make a dedicated personal-cloud server manageable like
an appliance. The current Nextcloud AIO implementation is an engineering pilot.

Pick work from [PRIORITIES.md](PRIORITIES.md), then read the [architecture](docs/ARCHITECTURE.md),
[roadmap](docs/ROADMAP.md) and [development checks](docs/CI.md). Open a pull
request against `main` with a concrete description of the behavior changed and
the checks you ran. `main` is protected: use a branch, wait for **Validate pilot**,
resolve review conversations, and squash or rebase merge. Update the priorities
tracker when completing an item. Add regression coverage when changing operation admission,
storage checks, backup evidence, recovery verification or authentication boundaries.

The first milestone is qualification of the existing Nextcloud path on a clean
Ubuntu Server 24.04 x86-64 VM. Work through [the acceptance checklist](docs/ACCEPTANCE.md)
and record versions, results and sanitized evidence. Prioritize failures in that
path before implementing another provider.

After qualification, improve onboarding: authenticated browser setup, clear disk
and hostname prerequisites, trustworthy HTTPS, backup status, guided restore,
and testing on actual phones. A downloadable VM image should follow a repeatable
install/update/recovery process. Keep routine operation independent of GitHub.

Use example hostnames and synthetic accounts in public issues and test fixtures.
Keep real configurations, passwords, private keys, manager snapshots and personal
file contents outside this repository. Screenshots and logs should contain only
the evidence needed to reproduce the issue.

A passing CI run covers local code and simulated UI behavior. Changing the
provider's readiness status requires the real-host evidence described in the
acceptance checklist.
