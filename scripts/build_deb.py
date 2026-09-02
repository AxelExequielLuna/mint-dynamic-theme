#!/usr/bin/env python3
"""Automata la creacion del .deb de mint-dynamic-theme con cada version.

Detecta la version desde mint_dynamic_theme/__init__.py, actualiza el
debian/changelog si hace falta y lanza scripts/build-deb.sh en contenedores
limpios por cada target (ubuntu:22.04, ubuntu:24.04, debian:12).

Reconstruye automaticamente cuando la version actual difiere de la ultima
construida (stamp en dist/deb/.last-built.json). Usa --force para forzar.

Uso:
    python3 scripts/build_deb.py [--targets ubuntu:24.04,debian:12]
                                 [--force] [--maintainer "Nombre <mail>"]
                                 [--check] [--out dist/deb]
"""
import argparse
import email.utils
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')
DEFAULT_TARGETS = ["ubuntu:24.04", "ubuntu:22.04", "debian:12", "debian:13"]
DEFAULT_MAINTAINER = "Axel Luna <me@axel-luna.com.ar>"


def read_version() -> str:
    init = (ROOT / "mint_dynamic_theme" / "__init__.py").read_text(encoding="utf-8")
    m = VERSION_RE.search(init)
    if not m:
        raise SystemExit("error: no se pudo leer __version__ de __init__.py")
    return m.group(1)


def slugify(image: str) -> str:
    return image.replace(":", "-").replace("/", "-")


def ensure_changelog(version: str, maintainer: str) -> None:
    changelog_path = ROOT / "debian" / "changelog"
    top = ""
    if changelog_path.exists():
        top = changelog_path.read_text(encoding="utf-8", errors="replace")
    first_line = top.splitlines()[0] if top else ""
    if f"{version}-1" in first_line:
        return
    stamp = email.utils.formatdate(localtime=True)
    entry = (
        f"mint-dynamic-theme ({version}-1) unstable; urgency=medium\n"
        f"\n"
        f"  * Nueva versión {version}.\n"
        f"\n"
        f" -- {maintainer}  {stamp}\n"
        f"\n"
    )
    if top.startswith("mint-dynamic-theme ("):
        changelog_path.write_text(entry + top, encoding="utf-8")
    else:
        changelog_path.write_text(entry, encoding="utf-8")


def last_built_state(out_dir: Path) -> dict:
    stamp = out_dir / ".last-built.json"
    if stamp.exists():
        try:
            return json.loads(stamp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_target(image: str, out_dir: Path, force: bool = False, version: str = "") -> bool:
    slug = slugify(image)
    target_dir = out_dir / slug
    artifacts = list(target_dir.glob(f"mint-dynamic-theme_{version}-1_*.deb"))
    if artifacts and not force:
        print(f"[skip] {image}: ya existe {artifacts[0].name}")
        return False
    for a in artifacts:
        a.unlink()
    print(f"[build] {image} (slug={slug}) …")
    subprocess.run(
        ["bash", str(ROOT / "scripts" / "build-deb.sh"), image, str(ROOT), str(target_dir)],
        check=True,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--targets",
        default=",".join(DEFAULT_TARGETS),
        help="imágenes base separadas por coma (default: %(default)s)",
    )
    parser.add_argument("--force", action="store_true", help="reconstruir aunque ya exista")
    parser.add_argument(
        "--maintainer",
        default=os.getenv("MDT_MAINTAINER", DEFAULT_MAINTAINER),
        help="mantenedor para debian/changelog",
    )
    parser.add_argument("--out", default=str(ROOT / "dist" / "deb"))
    parser.add_argument(
        "--check",
        action="store_true",
        help="solo mostrar versión y si hace falta construir, sin construir",
    )
    args = parser.parse_args()

    version = read_version()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]

    state = last_built_state(out_dir)
    built_version = state.get("version")
    built_targets = set(state.get("targets", []))
    pending = [t for t in targets if slugify(t) not in built_targets or args.force]

    print(f"Versión actual: {version}")
    print(f"Última construida: {built_version or '(ninguna)'}")

    if args.check:
        if version == built_version and not pending and not args.force:
            print("Sin cambios: no hace falta reconstruir.")
        else:
            print(f"Pendientes de construir: {', '.join(pending) if pending else '—'}")
        return 0

    ensure_changelog(version, args.maintainer)

    rebuilt = []
    for target in targets:
        slug = slugify(target)
        target_dir = out_dir / slug
        target_dir.mkdir(parents=True, exist_ok=True)
        artifacts = list(target_dir.glob(f"mint-dynamic-theme_{version}-1_*.deb"))
        if artifacts and not args.force:
            print(f"[skip] {target}: ya existe {artifacts[0].name}")
            continue
        try:
            build_target(target, out_dir, force=args.force, version=version)
            rebuilt.append(slug)
        except subprocess.CalledProcessError as e:
            print(f"[error] {target}: build fallido ({e})", file=sys.stderr)
            return 1

    artifacts = sorted(out_dir.glob(f"**/mint-dynamic-theme_{version}-1_*.deb"))
    if artifacts:
        lines = []
        for a in artifacts:
            lines.append(f"{sha256(a)}  {a.relative_to(out_dir)}")
        (out_dir / f"SHA256SUMS-{version}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        state = {"version": version, "targets": sorted({slugify(t) for t in targets} | built_targets)}
        (out_dir / ".last-built.json").write_text(
            json.dumps(state, indent=2), encoding="utf-8"
        )

    print("\nResumen:")
    for slug, origin in ((slugify(t), t) for t in targets):
        found = sorted(out_dir.glob(f"{slug}/mint-dynamic-theme_{version}-1_*.deb"))
        if found:
            print(f"  ✓ {origin}: {len(found)} arte(s) en {found[0].relative_to(ROOT)}")
        else:
            print(f"  - {origin}: sin artefacto")
    if rebuilt:
        print(f"Se reconstruyó para: {', '.join(rebuilt)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
