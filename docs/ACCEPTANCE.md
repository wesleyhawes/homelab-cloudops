# Real-host qualification checklist

**Status at packaging: not executed on a live homelab.** Local tests and browser mocks do not satisfy this document. Record host OS/architecture, Docker/Compose/Ansible/Semaphore/AIO versions, resolved image IDs, test date, backup identifiers and evidence for every result. Use disposable VMs and files.

| ID | Test | Pass condition |
|---|---|---|
| H01 | Clean-host bootstrap | Manager starts without Git checkout/account; no unrelated data is changed. |
| H02 | Native owner login/TOTP | Sign-in, logout, TOTP and recovery codes function through the actual HTTPS origin. |
| H03 | Local playbook provisioning | Exactly the intended project/templates/inventory exist; rerun does not reset secrets or duplicate resources. |
| H04 | Fixed SSH bridge | Allowed operations run; extra arguments, shell syntax, forwarding and arbitrary commands are rejected. |
| H05 | AIO deployment | Correct master name/volume/socket/ports; native child ownership intact; onboarding succeeds. |
| H06 | Idempotent second deployment | Existing data and credentials preserved; no container recreation/migration occurs unexpectedly. |
| H07 | Normal reboot | Correct mount is available before Docker; manager and application return appropriately. |
| H08 | Missing/wrong data mount | After controlled shutdown and disconnection of the disposable data disk, Docker fails closed without replacement writes. Restore the correct disk before recovery. |
| H09 | Conflicting/nonempty existing state | Unmanaged master, metadata volume and data directory are not adopted or overwritten. |
| H10 | Private network reachability | Only intended private endpoints are reachable; public WAN cannot access management. Verify Docker/firewall interactions. |
| H11 | Browser operations | On actual Android/iOS and laptop browsers, approve once, observe log, close tab/lock phone, reconnect to the same live task. |
| H12 | Semaphore failure during work | Host systemd job continues independently; failed console task is not mistaken for operation success. CLI history is recoverable. |
| H13 | Native first backup | AIO backup setup and passphrase handling work at the enrolled path. |
| H14 | CloudOps verified backup | Fresh completed Borg execution and archive evidence; application resumes. |
| H15 | Backup failure | Unavailable destination, read-only destination, capacity pressure and Borg error result in clear failure/attention, not stale success. |
| H16 | Concurrency | Competing CloudOps mutations denied; documented native-AIO coordination policy exercised. |
| H17 | Integrity check | Fresh check mode verified; not reported as a new backup or restore. |
| H18 | Distinct-host restore | Fresh isolated VM restored from the selected backup; original seeded fixture and anonymous denial pass. |
| H19 | Broader recovery | Representative files/shares/permissions/login/background jobs verified; no external emails/hooks/production clients contacted. |
| H20 | Wrong recovery target | Same-machine, wrong-hostname, corrupt fixture, invalid TLS and accidental primary routing fail verification. |
| H21 | Scheduled backup without manager/Git | Host timer can complete and records its status while Semaphore and Git services are unavailable. |
| H22 | Native application update | Supported version transition through AIO after verified backup; app/files/backup checked afterward. No image downgrade used as rollback. |
| H23 | Manager backup/recovery | SQLite snapshot plus corresponding configuration/encryption material recover the management installation on an isolated target. |
| H24 | Usability | A non-Ansible user completes the documented pilot flow; record points still requiring expert help rather than claiming full beginner readiness. |
| H25 | Security review | Real API authorization, cross-origin mutation handling, stored/reflected injection, secret paths and SSH privilege boundaries reviewed. |

Do not mark the provider “supported” until its required matrix is complete. Never run disk-removal, interrupted-migration or destructive recovery tests against the only copy of valuable data.
