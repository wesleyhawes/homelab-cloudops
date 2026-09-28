# Examples only

`config.example.json` uses a placeholder application hostname and private IP.
Replace them with your actual environment. Empty mount identities are enrolled
on the target host during first-run setup. Do not insert plaintext passwords.

`rendered/` contains previews generated from that example, not deployment files
for your server. The installer writes the actual runtime configuration under
`/etc/cloudops`. Nothing in this folder implies that any provider was installed.
