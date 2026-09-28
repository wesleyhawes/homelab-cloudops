# Roadmap after the implemented pilot

## Gate 1 — Qualify the current vertical slice

Run `ACCEPTANCE.md` on a dedicated Ubuntu VM and fix actual integration failures before expanding providers. Exercise the real Semaphore API and action plugin, private HTTPS/TOTP, storage boot dependency, native AIO onboarding, fresh backup evidence, mobile disconnect/reconnect and distinct-host restoration. Preserve a reproducible test transcript and version catalog.

## Gate 2 — Reduce remaining beginner friction

Move initial host/settings collection from the terminal to an authenticated browser setup flow; integrate safe hostname/certificate/private-access choices; offer a tested appliance/VM image; validate on real iOS and Android. Add backup-age and storage alerts, notification setup, manager backup scheduling, guided manager recovery and interruption reconciliation. Keep Git optional.

## Gate 3 — Add providers independently

Implement `owncloud_ocis`, then classic `owncloud_server` when demanded, and OxiCloud as experimental until its complete lifecycle passes. Each needs its own schema, topology, recovery set, probe and supported version transitions. Never reuse another provider's primary data directory. Upgrade readiness is more than first installation.

## Gate 4 — Release and security hardening

Publish signed artifacts and explicit hashes, a fully resolved dependency lock, exact platform-specific image digests for components the project owns, a repeatable OS/architecture qualification matrix, security scanning and release provenance. Maintain the distinction between upstream-managed AIO components and independently pinned ones. Add encrypted/off-host manager backup and original evidence import from remote restore-test hosts.

## Gate 5 — Broader platforms and optional integrations

Qualify Fedora Server with SELinux enforcing, then ARM64/Turing Pi where every selected upstream component supports it. Add GitLab/Gitea/GitHub wrappers, external monitoring and Data Profusion dashboard integration as **optional clients** of the existing operation engine. Do not replace host backup scheduling with CI or put secrets into a public portfolio repository.

A later custom Nextcloud Compose profile, multi-host control plane or Kubernetes backend should be separate deployment profiles with explicit maintenance ownership—not hidden complexity in the beginner path.
