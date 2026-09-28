# Adding ownCloud or OxiCloud without forking the product

## Registry and readiness are explicit

`src/cloudops/providers/__init__.py` defines the approved providers, their maturity, Ansible role and capabilities. Only `nextcloud_aio` executes in 0.1.0a1. `owncloud_ocis`, `owncloud_server` and `oxicloud` are intentionally distinct disabled entries. Selecting one yields a clear unsupported-provider error before deployment rather than substituting a Nextcloud template.

`contract.py` describes the initial adapter methods. `adapter_for()` is a code-reviewed mapping; it must not become an arbitrary module path loaded from configuration. Corresponding Ansible role directories are present but deliberately fail until implemented.

## Shared versus provider-owned work

| Shared engine | Provider-owned behavior |
|---|---|
| Host baseline and storage enrollment | Correct container topology and configuration. |
| Management authentication/task history | Identity, database, metadata and content consistency. |
| Admission, locking and systemd lifecycle | Native quiesce/resume and migration rules. |
| Confirmation and sanitized structured results | Evidence that a backup actually completed. |
| Backup/recovery evidence terminology | Application-specific restore and functional probes. |
| Mobile UI and optional future CI adapters | Supported version transitions and application administration. |

Do not presume the providers share a database, a data-directory schema, DAV endpoint paths or identity stack. Never implement a provider switch as reusing another provider's primary files or changing only the image name.

## Required operations and results

The first lifecycle interface uses `deploy`, `check`, `backup`, `backup_check`, `verify`, `recovery_info` and `verify_recovery`. New providers may advertise a subset while experimental. Browser actions must follow approved capability metadata, not imply support merely because a directory exists.

`prepare_deploy()` validates ownership and storage before any writes. `finish_deploy()` verifies the created service and states onboarding requirements explicitly. `health()` differentiates process availability from meaningful application readiness. `backup()` must produce a consistent application recovery set and fresh evidence. `verify_recovery()` must validate the original fixture on a distinct isolated host using provider-appropriate endpoints and identity semantics.

Common evidence keys include `checked_at`, `application_verified`, `backup_verified`, `integrity_verified`, `restore_verified`, timestamps and the scope of verification. An operation must not return `restore_verified: true` merely because a file copy or archive-integrity check completed. Secret-bearing Docker inspections, database credentials and application tokens must not be copied into results.

## ownCloud Infinite Scale adapter

Treat oCIS as its own application/identity/storage architecture, not classic ownCloud with a different tag. Identify all authoritative identity/configuration/metadata/content state, bind it to the recovery manifest, and validate logout/login/file/share behavior after restoration. Document supported proxy/identity requirements and architecture/image coverage for the exact selected release. Review the specific artifact's license/distribution terms before repackaging it.

## ownCloud Server adapter

Treat classic ownCloud separately: implement version-qualified application/database/cache topology, cron/background operations, maintenance and database export/restore. Prove that file storage and database metadata represent the same recovery point. Use its documented administrative and upgrade interfaces rather than Nextcloud-specific assumptions.

## OxiCloud adapter

Review the actual selected OxiCloud release at its current upstream location, then define application/PostgreSQL/file-storage state and migration behavior. Confirm available DAV endpoints and authentication semantics before reusing any verification logic. Start at experimental maturity and refuse unsupported architectures/upgrade paths. A successful first install is not enough for supported status.

## Steps for a new provider

1. Write a version-scoped provider design and configuration-schema migration; do not expand arbitrary command inputs.
2. Implement an adapter under `src/cloudops/providers/`, add it to the explicit factory, and create its Ansible lifecycle tasks.
3. Extend the host playbook's **approved role allowlist**, Compose rendering dispatch, provider-specific probe behavior, installer choices and generated browser capabilities together.
4. Add unit/contract tests plus disposable VM integration tests for installation, idempotency, credential preservation, reboot, backup, restoration and supported upgrades.
5. Preserve existing provider/state boundaries, and keep data migration a distinct explicitly approved workflow.
6. Move maturity from `planned` to `experimental` only when implemented, then to `supported` only after the recorded qualification matrix passes. Keep unsupported actions disabled.

The first configuration schema deliberately covers the Nextcloud pilot. Adding provider-specific fields requires a reviewed schema revision or a strictly validated provider-settings namespace; silently ignoring unknown configuration is not acceptable.
