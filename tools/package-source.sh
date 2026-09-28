#!/usr/bin/env bash
# Package a committed source tree, including installer and runtime assets.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
output="${1:-local/ci/dist}"
mkdir -p "$output"
commit="$(git rev-parse --verify HEAD)"
archive="homelab-cloudops-source-${commit:0:12}.tar.gz"
git archive --format=tar --prefix=homelab-cloudops/ "$commit" | gzip -n > "$output/$archive"
(
  cd "$output"
  sha256sum "$archive" > "$archive.sha256"
  sha256sum --check "$archive.sha256"
)
printf 'Packaged commit %s in %s/%s\n' "$commit" "$output" "$archive"
