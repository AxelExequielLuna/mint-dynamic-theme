#!/usr/bin/env bash
# Construye el paquete .deb de mint-dynamic-theme dentro de una imagen base limpia.
#
# Uso:
#   build-deb.sh <imagen-base> <dir-repo> <dir-salida> [url-git]
#
# Ejemplos:
#   scripts/build-deb.sh ubuntu:24.04 "$PWD" dist/deb/ubuntu-24.04
#   scripts/build-deb.sh debian:12    "$PWD" dist/deb/debian-12
set -euo pipefail

BASE_IMAGE="${1:?imagen base requerida (ej: ubuntu:24.04)}"
REPO_DIR="${2:?directorio del repo requerido}"
OUT_DIR="${3:?directorio de salida requerido}"
GIT_URL="${4:-}"

if ! command -v docker >/dev/null 2>&1; then
    echo "error: se requiere docker" >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "error: el daemon de docker no responde" >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

# Hacer visible el último commit en el changelog generado (opcional).
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
echo "--- artefactos generados ---"
ls -la /out/*.deb
'

echo "ok: .deb en $OUT_DIR"