# Network and HTTPS access

## Ports and boundaries

| Endpoint | Default binding | Purpose |
|---|---|---|
| CloudOps management | selected private IPv4:9443, HTTPS | Static mobile portal and proxied Semaphore UI/API. |
| Semaphore direct | 127.0.0.1:3000 | Local management service and first-run provisioning. Not a public listener. |
| Management proxy input | 127.0.0.1:9080, HTTP | An existing **trusted HTTPS** host proxy may front this endpoint. |
| AIO native setup | selected private IPv4:8080, HTTPS | Upstream AIO's separate management interface. |
| Cloud application upstream | 127.0.0.1:11000, HTTP | AIO's Apache endpoint for a host-side application reverse proxy. |
| SSH operation bridge | host SSH service | Key-restricted, forced-command execution from the manager. |

Do not expose ports 3000, 9080, 8080, 9443 or the operation bridge to the public internet. If you later publish the cloud application, that is a separate deliberate decision. Router forwarding is not configured automatically. Docker-published ports interact with host firewall rules differently from ordinary host processes; verify actual reachability from another device rather than relying on a UFW rule alone.

## Direct private HTTPS management

Caddy generates a local CA and an IP-address certificate for the selected private interface. The installer tries to copy the public root certificate to `/root/cloudops-management-ca.crt`. If issuance has not occurred yet, inspect Caddy logs and retrieve the public certificate after it is initialized:

```bash
sudo docker compose -f /etc/cloudops/manager.compose.yaml exec -T gateway \
  cat /data/caddy/pki/authorities/local/root.crt
```

Use the local console or your verified SSH connection to establish the certificate's identity. Obtain its SHA-256 fingerprint with `openssl x509 -in /root/cloudops-management-ca.crt -noout -fingerprint -sha256`. Transfer only the public certificate to the devices you own, and use their documented trust-installation process. This is a small private CA; compromise of its private key matters. Never send that private key to a phone simply to make the certificate work.

This version does not distribute trust profiles automatically. A polished trust/onboarding flow is a subsequent usability milestone.

## Existing application proxy

The cloud application must have a hostname, a certificate the relevant clients trust, and a route to this host's loopback Apache endpoint. Follow AIO's reverse-proxy guidance in `SOURCES.md`, including large-upload behavior, timeouts and proxy headers. Do not proxy the normal application to the AIO admin port.

An example **fragment for an existing host-side Caddy configuration**, not the manager Caddyfile, is:

```caddyfile
cloud.your-actual-domain.example {
    reverse_proxy 127.0.0.1:11000
}
```

Replace the hostname and configure certificate issuance appropriate to your environment. The fragment alone does not arrange DNS, DNS-provider credentials, reachability or private certificate trust. It is not an instruction to publish management or open router ports. Do not add it blindly to another proxy that already owns the hostname.

## Optional private remote access

An existing VPN can route approved devices to the private management address. An optional Tailscale installation may provide another path, but its external account/control-service dependency is not a CloudOps requirement.

Tailscale Serve is a private tailnet exposure mechanism; Funnel is a different, public feature and should not be enabled for management. The current Serve syntax permits private HTTPS forwarding to a local port, for example forwarding a management HTTPS port to `http://127.0.0.1:9080`. Review the official Serve documentation, hostname/certificate requirements and tailnet ACLs before configuring it.

When placing Semaphore behind a **different public-facing hostname or port**, configure its `SEMAPHORE_WEB_HOST` consistently in the reviewed manager Compose configuration and validate native login, TOTP, cookies and redirects through that exact origin. This advanced proxy variation is not covered by the package's local browser mocks. Rerunning the bootstrap regenerates Compose from its own selected private address; do not use bootstrap as a settings editor.

## AIO's initial certificate

The native 8080 setup page deliberately differs from normal cloud access: upstream uses an IP-based self-signed certificate for first-run management. Use a verified private connection and confirm the server identity through your console/SSH path and upstream procedure. It is not signed by the CloudOps management CA. Normal application access still requires the configured hostname and valid trusted HTTPS.

## No hidden public endpoint

The installer does not create an OAuth client, external user account, public tunnel, public control-plane service or telemetry endpoint. Initial APT/PyPI/image downloads and the upstream applications' own network behavior remain separate considerations; no claim is made that upstream applications never contact their update infrastructure.
