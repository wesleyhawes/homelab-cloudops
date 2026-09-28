# Operating the pilot

## Normal workflow

Use the mobile portal to launch an operation, read the confirmation when shown, and observe its output under Activity. Do not infer success from the mere presence of a running container, from a green CI icon, or from an old backup record. Refresh “Check my cloud” after significant changes. The internal health check verifies Nextcloud's installed/maintenance/database state, not end-to-end internet reachability.

The native Semaphore console remains available for task detail. Accounts with project task-running access can execute project templates; hiding a button is not an authorization boundary. The initial manager is intended for a trusted owner. Family file users belong in the cloud application, not in the privileged management project.

## Host commands and diagnosis

```bash
sudo cloudctl history
sudo cloudctl follow <32-character-host-job-id>
sudo systemctl status cloudops-<32-character-host-job-id>
sudo journalctl -u cloudops-<32-character-host-job-id>
sudo docker compose -f /etc/cloudops/manager.compose.yaml ps
sudo docker compose -f /etc/cloudops/manager.compose.yaml logs --tail 100
```

Review logs locally before sharing them. Project-generated status excludes known credentials, but logs from upstream applications or errors can still contain personal metadata. There is not yet an automatically redacted support-bundle exporter.

## Backups

Use AIO's first-run backup configuration and save its Borg passphrase outside the cloud. CloudOps requires the configured local backup mount to match its enrolled path and a first Borg container to exist. Its subsequent native backup check requires:

1. A fresh Borg execution in the requested mode.
2. Start/finish times consistent with this request, stopped state and exit code zero.
3. The upstream success message in logs from this request.
4. A newly listed archive for a backup operation.
5. Nextcloud returning to its internal healthy state after backup.

Backup evidence is stored before checking restart health. A backup may therefore exist while the overall operation requires attention because application startup failed. Read the actual outcome rather than retrying blindly. Evidence parsing is version-sensitive; upstream changes should fail closed and trigger adapter requalification.

“Check backup integrity” invokes AIO's native Borg data-integrity check. It is not a fresh backup and not an application restore test. Basic free-space checks do not predict the exact size of the next backup.

## Scheduling

Only one schedule should initiate AIO maintenance. After a verified CloudOps backup, disable AIO's native daily schedule and run `sudo cloudctl enable-backup-timer`. Inspect it with `systemctl list-timers cloudops-backup.timer`. The default schedule is 03:00 in the configured timezone with up to five minutes random delay. The timer is persistent, so a missed run can trigger after the server returns; plan around that behavior.

The timer does not require Semaphore, Git or an open browser. A failure remains visible in host job history/systemd, but external email/push alerts are not automatically configured in this release. Configure your normal homelab monitoring for failed backup jobs before relying on scheduled protection.

To pause the CloudOps schedule while doing native maintenance:

```bash
sudo systemctl disable --now cloudops-backup.timer
```

This does not stop a backup already executing. Inspect the job and AIO before making changes.

## Updates

There is intentionally no `cloudctl upgrade` in this pilot. For native AIO updates, ensure no CloudOps or native operation is running, pause the CloudOps timer, review AIO/application upgrade prerequisites, perform a fresh verified backup, save recovery information, and use the supported AIO update flow. Afterwards run `check`, `verify`, a controlled file upload/download and another backup. Re-enable the timer only after verification.

Do not point an old image at a migrated database. Native Nextcloud downgrades are unsupported; recovery requires the compatible backup set and version, with an explicit understanding of any data written after that backup. Do not enable a general image auto-updater alongside AIO's own maintenance ownership.

Manager updates are manual, version-reviewed changes. Do not rerun bootstrap while jobs are active; it refuses active/attention records. The installer is not an unattended manager-update mechanism, and a fully locked rollbackable manager release workflow is future work.

## Interrupted work

An attention state blocks later mutations. Inspect the host job, underlying AIO containers, native lock status, filesystem and latest backup. Only after understanding the state:

```bash
sudo cloudctl acknowledge <host-job-id>
```

The command refuses when the systemd operation is active or Borg/update work is visibly running. It asks for the exact job ID. It records operator acknowledgement, not success or proof that a migration was rolled back. It does not silently remove AIO's own lock file.

## Missing storage at reboot

The Docker service is bound to the required data mount and runs identity/capacity checks before startup. This affects **all containers on this dedicated host**, including the manager. If the mount is missing or below its reserve, browser management may be unavailable; the local/SSH console is the recovery path.

Inspect `findmnt`, the relevant `.mount` unit, `systemctl status docker` and the journal. Restore the correct mount identity before starting Docker. Never “fix” the check by creating an empty directory or bypassing identity validation. The systemd dependency reacts to mount-unit state; it is not a guarantee that every storage I/O failure will be detected immediately.
