# Backup and recovery runbook

**A successful backup, a repository-integrity check and a successful application restoration are three different results.** This pilot keeps them separate. The optional automated recovery probe validates only a dedicated account, one seeded file and anonymous denial; complete the broader manual checks below as well.

## A. Protect the right recovery material

Keep these outside the cloud being protected:

* The complete native AIO Borg repository and its passphrase, plus a known good recovery point and application-version record.
* The CloudOps release package, non-secret configuration kit and original probe manifest.
* The separately protected probe account app password, and the manager's own SQLite/configuration/encryption keys when restoring management history matters.
* DNS, proxy, certificate, storage-mount and access instructions required to bring up a replacement host.

A second directory on the same filesystem is rejected, but a different filesystem can still share a physical device or failure domain. Use independent off-host protection. Do not store the only decryption key or recovery instructions inside Nextcloud.

## B. Enroll a small verification fixture

Create a dedicated, non-admin Nextcloud account with minimal quota and an app password. Do not use a real user's master password. On the **primary** host after native onboarding:

```bash
sudo cloudctl probe-credentials
sudo cloudctl probe-enroll
sudo cloudctl run backup
sudo cloudctl export-recovery /root/cloudops-recovery-kit.tar.gz
```

Enrollment uploads a new randomly named 512-byte file using WebDAV with a no-overwrite precondition, reads it back, stores its checksum and source machine identifier, and checks anonymous denial. The file must be in the selected backup: take a verified backup **after** enrollment.

`export-recovery` creates a **NON-SECRET configuration/manifest kit, not a data backup and not a manager backup**. Credentials are deliberately excluded. Copy the kit and separately protected probe credential `/etc/cloudops/secrets/probe.json` to independent storage through a trusted process. Never expose the credential in browser logs or public repositories.

## C. Prepare an isolated recovery host

Use a fresh VM with a distinct `/etc/machine-id`, not a cloned primary masquerading as another host. Prepare new, correctly mounted data storage and a **separate working copy** of the backup repository. Pause writers before copying a repository and do not have two hosts maintain/prune the same live repository concurrently.

Use local DNS/network isolation to prevent the restored cloud from receiving production clients or reaching production integrations. Pull required images before tightening egress. Block or neutralize restored email delivery, webhooks, federation, background integrations and sync clients. An original-hostname restore can have the same application identity as production, so isolation is mandatory.

The restored application should retain its original cloud hostname and expected data path, but on the new isolated host. Arrange a private HTTPS proxy on port 443 with a certificate valid for that original hostname and trusted by the verification client. Do not change production DNS. When needed, install the appropriate **public** private-CA certificate at `/etc/cloudops/probe-ca.pem`; the client continues to verify TLS and does not provide an insecure-skip option.

Use a reviewed recovery configuration with `mode: "recovery-test"`, the recovery host's actual private IPv4 address, and freshly enrolled storage identities. Do not blindly copy the primary config's hardware identities or job database. The installer is interactive or accepts reviewed JSON with empty identities for enrollment.

## D. Restore through AIO's supported interface

Install the manager on the new host, use “Install cloud” to create its AIO mastercontainer, then follow the native AIO restoration workflow with the working Borg repository copy, passphrase and chosen archive. Keep the restore host isolated throughout the process. The backup path exposed to AIO must match the recovery host's enrolled backup path.

Do not manually substitute a database image, write private AIO configuration APIs, run `down -v`, or attempt a fake rollback with an older application image. The package deliberately does not expose an unattended destructive restore action.

Only when AIO restoration has completed and the application is healthy, import the **original** manifest from the non-secret kit:

```bash
sudo install -m 0600 /trusted/recovery-kit/probe-manifest.json /var/lib/cloudops/probe-manifest.json
sudo install -m 0600 /trusted/protected/probe.json /etc/cloudops/secrets/probe.json
sudo cloudctl run verify_recovery
```

The source paths above are placeholders for files you have safely retrieved; no extraction or overwrite of the new server's configuration is implied. Alternatively use “Verify recovered files” on the recovery host's browser console. Never enroll a new fixture on that host and call its presence a restored file.

## E. What the automated probe proves

The verifier requires recovery-test mode and a different machine identity. Its HTTPS connection is pinned to the configured recovery-host address while retaining certificate verification for the original hostname, to avoid accidentally reading from the live primary through normal DNS. It requires the original file's exact size/SHA-256 and anonymous access denial.

Passing evidence is saved to `/var/lib/cloudops/last-restore-test.json` **on the recovery host**. The primary manager does not automatically import remote results in this release. Retain the report with your recovery-test record; do not manually substitute an old or unrelated report merely to obtain a green card.

This is a scoped sample check, not cryptographic attestation against a malicious root operator and not validation of every file, user, group, share, application or encryption-key scenario.

## F. Complete the manual acceptance checks

Verify representative additional file checksums, owner/group permissions, public/private shares as appropriate, application login and logout, a fresh upload/download, background jobs, selected application features and absence of unintended external traffic. Record the backup archive, installed/resolved application versions, data loss window, elapsed recovery time, test host identity and limitations.

Do not advertise a recovery-time objective until measured in your own drills. A restore to an older recovery point can lose newer data; communicate that explicitly before a real disaster-recovery cutover. A planned provider migration is separate work.

## G. Recover management separately

The application backup does not automatically protect Semaphore. Manager recovery needs its SQLite database, configuration, access-key-encryption key, credentials/bridge key, CA material when retaining trust, CloudOps configuration and the matching release. A non-secret kit alone cannot recover all of those.

`cloudctl manager-backup <new-path.tar.gz>` creates an owner-only **plaintext** manager snapshot on the server using SQLite's online backup API. It refuses active host jobs and includes sensitive configuration/keys. Encrypt it and move it to independently protected storage before treating it as an off-host backup. It is not scheduled automatically and never includes the AIO application data repository.

Recovering manager history on a replacement host is an advanced, manual operation in this pilot: do not restore the primary host's storage identities blindly; review the new mount identities, bridge host key, addresses and certificate trust. Retain the matching manager version, restore the database and its access-key encryption material together, and validate login/TOTP/operation permissions before enabling maintenance. A fully automated manager restore is not implemented.

## H. Recovery is never dependent on Git

Keep a copy of the release and this runbook outside Git-hosted services and outside the cloud. A direct operator can inspect jobs, invoke native AIO recovery or rebuild the manager without GitLab, Gitea, GitHub or a CI runner.
