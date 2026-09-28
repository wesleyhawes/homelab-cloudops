# Start here — CloudOps 0.1.0a1

## 1. Preview without changing a server

Extract the archive and run the following from its `homelab-cloudops` directory:

```bash
python3 tools/preview.py
```

Visit `http://127.0.0.1:8765/cloudops/` on the same laptop. Use the simulated session link. No Docker, Ansible installation, root permission, Git account or real credential is needed for this preview. Stop with Ctrl+C.

The preview is not an installation and cannot manage anything. Its health/backup values are simulated and clearly labeled.

## 2. Prepare a disposable reference host

Use a fresh **Ubuntu Server 24.04 x86-64 VM** with systemd, console/SSH access and outbound internet access. A practical planning starting point is 4 virtual CPUs and 8 GiB RAM for the small pilot, with additional capacity based on selected AIO features; this is a suggested lab allocation, not an upstream minimum or a performance guarantee. Size the OS disk for Docker images, volumes and application growth, not merely the management UI.

Use a dedicated VM even when the physical hypervisor runs Fedora. Do not initially install this onto Donnager's host OS, a shared Docker server or the ARM64 Turing Pi nodes. Existing Docker containers cause fresh installation to refuse, and the installer deliberately adds a service-wide Docker storage dependency.

Prepare two real mounted storage destinations **before** running the installer. The default layout is:

```text
/srv/cloud-data          separate ext4 or XFS data filesystem
/srv/cloud-data/nextcloud
/srv/cloud-backup        different filesystem, preferably off-host storage
/srv/cloud-backup/aio
```

Mount them persistently using stable identifiers, confirm the paths with `findmnt`, and understand their actual failure domains. The installer will not partition, format, erase, or select a disk for you. A data mount that disappears later must not be silently replaced by an empty directory on the OS disk.

Plan a private server address, an actual application hostname, and the application HTTPS route. See `docs/ACCESS.md`. No public management endpoint is necessary.

## 3. Run the local installer

Copy the extracted directory to the test VM through your normal trusted transfer method. From that directory:

```bash
sudo bash install.sh
```

Review the dedicated-server warning and type `DEDICATED` only on the intended test host. The installer can install Docker Engine from its official APT repository when Docker is absent. It also installs the host Python/Ansible environment, a restricted SSH operation bridge, Caddy and Semaphore via Docker Compose.

Answer the terminal questions. Use the server's **actual private IPv4 address**, not `127.0.0.1`, for direct phone/laptop access. The loopback default is intentionally unreachable from other devices. Replace `https://cloud.example.com` with the actual cloud hostname; the example is not installable.

Advanced users may copy `examples/config.example.json`, replace its example hostname and private address, and run:

```bash
sudo bash install.sh --config /path/to/reviewed-config.json
```

Leave empty mount identities for first-run enrollment. Do not copy identities from a different physical filesystem. On a configured host the installer preserves the existing configuration; it is not a general-purpose settings editor or application-upgrade command.

## 4. Open management securely

The installer prints an address resembling:

```text
https://192.168.10.50:9443/cloudops/
```

Use the actual address it prints. Direct-IP management uses Caddy's local CA. Transfer the exported public certificate `/root/cloudops-management-ca.crt` over a trusted path, verify its fingerprint on the server, and install trust on your own devices. Do not distribute the CA private key. Alternatively, use the separately documented trusted private proxy route.

The Semaphore owner username is `admin`. Retrieve the generated password **locally on the server**, not through browser logs:

```bash
sudo cat /etc/cloudops/secrets/admin_password
```

Sign in through the advanced console, enable TOTP two-factor authentication, save recovery codes outside this cloud, then return to `/cloudops/` and bookmark it. The mobile page uses that session; no permanent API token is placed in browser storage. If you change the owner's password, the initial seed-password file is no longer a valid API login for re-provisioning; normal operation does not require re-provisioning.

## 5. Install Nextcloud and finish native onboarding

Use **Install cloud**, review the confirmation, and open the private AIO setup address. This starts the AIO mastercontainer only. Complete AIO's supported first-run setup, save its separate management passphrase, select application components, and configure the actual cloud hostname.

AIO's initial IP-based management endpoint on port 8080 uses its own self-signed certificate. Its identity must be verified through your trusted server/SSH path and upstream onboarding instructions; it is distinct from the application HTTPS certificate and CloudOps's CA. Do not normalize ignoring arbitrary browser certificate warnings.

AIO's application Apache endpoint is bound to `127.0.0.1:11000` on the host for the chosen host-side proxy. A proxy running in another container cannot use its own loopback address to reach that host endpoint.

## 6. Configure and verify protection

In AIO, set the exact backup path selected during setup and finish the first native backup. Store the Borg passphrase in an independent password manager or protected offline record. Then run **Back up now** in CloudOps. It checks fresh Borg exit/mode/time evidence, a success marker and a newly reported archive; it does not trust a successful helper invocation alone.

Run **Check my cloud** to refresh the summary. The summary is a timestamped observation, not a continuously live availability guarantee.

For real recovery verification, create the dedicated probe account, enroll the file, take another verified backup, and follow `docs/RECOVERY.md` on a separate isolated VM. The complete acceptance checklist is in `docs/ACCEPTANCE.md`.

## 7. Enable a single backup schedule

Only after a verified CloudOps backup, disable AIO's native daily schedule and then explicitly enable the host schedule:

```bash
sudo cloudctl enable-backup-timer
sudo systemctl list-timers cloudops-backup.timer
```

The default is 03:00 in the configured timezone, with a small randomized delay. It works without a browser or Git platform. It is not enabled by the initial installer. Existing native AIO work remains a competing authority that the operator must avoid; a lock cannot coordinate arbitrary manual interventions that bypass this project.

**The next milestone is a recorded clean-host deployment, reboot/missing-mount test, verified backup and separate-host restore on your equipment. Until that evidence exists, this is a development pilot, not a production appliance.**
