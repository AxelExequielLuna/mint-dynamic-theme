#!/usr/bin/env bash
# Builds the mint-dynamic-theme .deb package inside a clean base image.
#
# Usage:
#   build-deb.sh <base-image> <repo-dir> <out-dir> [git-url]
#
# Examples:
#   scripts/build-deb.sh ubuntu:24.04 "$PWD" dist/deb/ubuntu-24.04
#   scripts/build-deb.sh debian:12    "$PWD" dist/deb/debian-12
set -euo pipefail

BASE_IMAGE="${1:?base image required (e.g. ubuntu:24.04)}"
REPO_DIR="${2:?repo directory required}"
OUT_DIR="${3:?output directory required}"
GIT_URL="${4:-}"

if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker is required" >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "error: the docker daemon is not responding" >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

# Make the last commit visible in the generated changelog (optional).
if [ -n "$GIT_URL" ]; then
    GIT_URL_ARG="-v ${GIT_URL}:/src/url:ro"
else
    GIT_URL_ARG=""
fi

docker run --rm \
    -v "$REPO_DIR:/repo:ro" \
    -v "$OUT_DIR:/out" \
    $GIT_URL_ARG \
    "$BASE_IMAGE" bash -c '
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq \
    debhelper \
    dh-virtualenv \
    python3 \
    python3-venv \
    python3-setuptools \
    python3-virtualenv \
    build-essential \
    >/dev/null

rm -rf /tmp/mdtbuild
mkdir -p /tmp/mdtbuild
cp -a /repo/. /tmp/mdtbuild/
cd /tmp/mdtbuild
rm -rf build dist *.egg-info __pycache__
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true

dpkg-buildpackage -b -us -uc

cp /tmp/*.deb /out/ 2>/dev/null || true
chmod 644 /out/*.deb 2>/dev/null || true
echo "--- generated artifacts ---"
ls -la /out/*.deb
'

echo "ok: .deb in $OUT_DIR"