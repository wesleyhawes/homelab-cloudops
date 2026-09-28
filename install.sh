#!/usr/bin/env bash
# Reviewed local bootstrap; no curl | bash and no Git checkout.
set -Eeuo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ ${EUID} -eq 0 ]] || { echo "Run: sudo bash install.sh" >&2; exit 1; }
source /etc/os-release
[[ ${ID:-} == ubuntu && ${VERSION_ID:-} == 24.04 && $(uname -m) == x86_64 ]] || {
  echo "This pilot installs only on Ubuntu Server 24.04 x86_64. Fedora/ARM64 are not yet qualified." >&2; exit 1;
}
[[ -d /run/systemd/system ]] || { echo "A real systemd host/VM is required; do not install inside this development container." >&2; exit 1; }
[[ -f "$ROOT/pyproject.toml" && -d "$ROOT/src/cloudops" ]] || exit 1
if [[ ! -f /etc/cloudops/config.json ]]; then
  printf '\nCloudOps 0.1.0a1 — disposable dedicated-server pilot.\n'
  printf 'Installs Docker (when absent), an SSH operation bridge and a private management UI.\n'
  printf 'Protects Docker startup with a data-mount guard that affects ALL Docker containers.\n'
  printf 'Never formats disks. Existing application adoption is not supported.\n'
  read -r -p 'Type DEDICATED to proceed on a dedicated test host: ' answer
  [[ "$answer" == DEDICATED ]] || exit 1
fi
if command -v docker >/dev/null 2>&1 && [[ ! -f /etc/cloudops/config.json ]]; then
  [[ -z "$(docker ps -aq)" ]] || { echo "Existing containers found. Use a fresh dedicated VM instead." >&2; exit 1; }
fi
if [[ -f /var/lib/cloudops/jobs.sqlite ]]; then
  python3 - <<'CHECK_JOBS'
import sqlite3, sys
with sqlite3.connect("file:/var/lib/cloudops/jobs.sqlite?mode=ro", uri=True) as db:
    count = db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','attention')").fetchone()[0]
if count:
    sys.exit("Existing operations need inspection. Finish or acknowledge them before rerunning the installer.")
CHECK_JOBS
fi
apt-get update
apt-get install -y python3 python3-venv python3-pip openssh-server openssh-client sudo ca-certificates curl gnupg
if ! command -v docker >/dev/null 2>&1; then
  for pkg in docker.io docker-compose docker-compose-v2 podman-docker containerd runc; do
    if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q 'install ok installed'; then
      echo "Conflicting package $pkg found; automatic removal is disabled. Use a clean Docker host." >&2; exit 1
    fi
  done
  install -d -m 0755 /etc/apt/keyrings
  curl --fail --show-error --silent --location --proto '=https' --tlsv1.2 \
    https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod 0644 /etc/apt/keyrings/docker.asc
  cat > /etc/apt/sources.list.d/cloudops-docker.sources <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
  chmod 0644 /etc/apt/sources.list.d/cloudops-docker.sources
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
docker info >/dev/null
docker compose version
if docker info --format '{{.DockerRootDir}}' | grep -q '/var/snap/'; then
  echo "Snap-based Docker is not supported." >&2; exit 1
fi
RELEASE=/opt/cloudops/releases/0.1.0a1
install -d -m 0755 /opt/cloudops/releases "$RELEASE"
if [[ "$ROOT" != "$RELEASE" ]]; then
  cp -a "$ROOT/." "$RELEASE/"
fi
chown -R root:root "$RELEASE"
chmod -R go-w "$RELEASE"
ln -sfn "$RELEASE" /opt/cloudops/current
python3 -m venv /opt/cloudops/venv
/opt/cloudops/venv/bin/python -m pip install --disable-pip-version-check "$RELEASE[automation]"
# Dependency resolution is networked. Record installed versions; this is not a fully locked offline release.
install -d -m 0700 /var/lib/cloudops
/opt/cloudops/venv/bin/python -m pip freeze > /var/lib/cloudops/python-installed.txt
ln -sfn /opt/cloudops/venv/bin/cloudctl /usr/local/bin/cloudctl
exec /opt/cloudops/venv/bin/python -I -m cloudops.setup "$@"
