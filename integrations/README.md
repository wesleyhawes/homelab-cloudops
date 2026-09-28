# Optional Git-platform integration — deliberately secondary

GitHub Actions now validates contributions to this repository; see
[`docs/CI.md`](../docs/CI.md). The distribution can still be downloaded/extracted,
installed, operated and recovered without a Git account or server. Git-hosted
project development and end-user operation are separate concerns.

Later GitLab, Gitea and GitHub wrappers should call the same approved host operations. Use protected deployment identities, explicit approval, isolated runners and existing host-side admission; never add a second unlocked deployment implementation or depend on CI for routine backups. A runner must not receive an unrestricted root key or Docker socket merely for convenience.

Separate untrusted contribution tests from privileged homelab operations. Native platform authorization and workflow behavior must be validated separately; copying GitHub YAML into Gitea is not proof of equivalent approval protection. The wrapper deliverables follow standalone qualification rather than delaying it.
