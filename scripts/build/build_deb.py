#!/usr/bin/env python3
"""Automates the creation of the mint-dynamic-theme .deb for each version.

Detects the version from src/mint_dynamic_theme/__init__.py, updates the
packaging/debian/changelog if needed and launches scripts/build/build-deb.sh in
clean containers for each target (ubuntu:22.04, ubuntu:24.04, debian:12).

Automatically rebuilds when the current version differs from the last built
one (stamp in dist/deb/.last-built.json). Use --force to override.

Usage:
    python3 scripts/build/build_deb.py [--targets ubuntu:24.04,debian:12]
                                 [--force] [--maintainer "Name <mail>"]
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

ROOT = Path(__file__).resolve().parents[2]
VERSION_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')
DEFAULT_TARGETS = ["ubuntu:24.04", "ubuntu:22.04", "debian:12", "debian:13"]
DEFAULT_MAINTAINER = "Axel Luna <me@axel-luna.com.ar>"


def read_version() -> str:
    init = (ROOT / "src" / "mint_dynamic_theme" / "__init__.py").read_text(encoding="utf-8")
    m = VERSION_RE.search(init)
    if not m:
        raise SystemExit("error: could not read __version__ from __init__.py")
    return m.group(1)


def slugify(image: str) -> str:
    return image.replace(":", "-").replace("/", "-")


def ensure_changelog(version: str, maintainer: str) -> None:
    changelog_path = ROOT / "packaging" / "debian" / "changelog"
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
        f"  * New version {version}.\n"
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
        print(f"[skip] {image}: {artifacts[0].name} already exists")
        return False
    for a in artifacts:
        a.unlink()
    print(f"[build] {image} (slug={slug}) …")
    subprocess.run(
        ["bash", str(ROOT / "scripts" / "build" / "build-deb.sh"), image, str(ROOT), str(target_dir)],
        check=True,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--targets",
        default=",".join(DEFAULT_TARGETS),
        help="comma-separated base images (default: %(default)s)",
    )
    parser.add_argument("--force", action="store_true", help="rebuild even if it already exists")
    parser.add_argument(
        "--maintainer",
        default=os.getenv("MDT_MAINTAINER", DEFAULT_MAINTAINER),
        help="maintainer for debian/changelog",
    )
    parser.add_argument("--out", default=str(ROOT / "dist" / "deb"))
    parser.add_argument(
        "--check",
        action="store_true",
        help="only show version and whether a build is needed, without building",
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

    print(f"Current version: {version}")
    print(f"Last built: {built_version or '(none)'}")

    if args.check:
        if version == built_version and not pending and not args.force:
            print("No changes: no rebuild needed.")
        else:
            print(f"Pending builds: {', '.join(pending) if pending else '—'}")
        return 0

    ensure_changelog(version, args.maintainer)

    rebuilt = []
    for target in targets:
        slug = slugify(target)
        target_dir = out_dir / slug
        target_dir.mkdir(parents=True, exist_ok=True)
        artifacts = list(target_dir.glob(f"mint-dynamic-theme_{version}-1_*.deb"))
        if artifacts and not args.force:
            print(f"[skip] {target}: {artifacts[0].name} already exists")
            continue
        try:
            build_target(target, out_dir, force=args.force, version=version)
            rebuilt.append(slug)
        except subprocess.CalledProcessError as e:
            print(f"[error] {target}: build failed ({e})", file=sys.stderr)
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

    print("\nSummary:")
    for slug, origin in ((slugify(t), t) for t in targets):
        found = sorted(out_dir.glob(f"{slug}/mint-dynamic-theme_{version}-1_*.deb"))
        if found:
            print(f"  ✓ {origin}: {len(found)} artifact(s) in {found[0].relative_to(ROOT)}")
        else:
            print(f"  - {origin}: no artifact")
    if rebuilt:
        print(f"Rebuilt for: {', '.join(rebuilt)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
