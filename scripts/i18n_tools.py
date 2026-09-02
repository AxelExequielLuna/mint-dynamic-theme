#!/usr/bin/env python3
"""Keep the i18n catalogs in sync with the ``_()`` strings in the code.

Scans the ``mint_dynamic_theme`` package for ``_("...")`` / ``translate("...")``
calls and manages the translation catalogs under
``mint_dynamic_theme/locales/<lang>/messages.json``.

Subcommands:
    update   Add missing source strings to every catalog (new keys get the
             original English string as a placeholder so the catalog stays
             safe at runtime; existing translations are never overwritten).
             Also removes keys that no longer exist in the code (orphans) and
             sorts keys alphabetically. The source-language catalog (``en``)
             is left as-is by default because it is just an identity mirror
             of the code; pass ``--all`` to populate it too.

    check    Report (and fail with exit code 1 when enabled) the current sync
             state:
               - source strings missing from a catalog
               - orphan keys (present in a catalog but not in the code)
               - untranslated placeholders (value == english source) for
                 languages other than the source language

Usage:
    python3 scripts/i18n_tools.py update [--lang es] [--no-remove] [--all]
    python3 scripts/i18n_tools.py check  [--lang es] [--strict]

Options:
    --lang <code>   Restrict the operation to a single catalog.
    --no-remove     With ``update``, keep orphan keys instead of removing them.
    --all           With ``update``, also populate the source-language catalog.
    --strict        With ``check``, exit non-zero if any issue is found.
                    (Without it, ``check`` only prints and exits 0.)
"""

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "mint_dynamic_theme"
LOCALES_DIR = PKG / "locales"

SOURCE_LANG = "en"

# Functions whose first string argument marks a translatable string.
TRANSLATION_FUNCS = ("_", "translate")


def find_py_files() -> list:
    """Return all source .py files in the package, excluding i18n itself."""
    files = []
    for p in PKG.rglob("*.py"):
        if p.name == "i18n.py":
            continue
        files.append(p)
    return sorted(files)


def extract_strings() -> list:
    """Return a sorted, de-duplicated list of translatable source strings."""
    found = set()

    for path in find_py_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        # Walk every node of the module.
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = _func_name(node.func)
            if func_name not in TRANSLATION_FUNCS:
                continue
            if not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                found.add(first.value)

    return sorted(found)


def _func_name(func) -> str:
    # Handles ``_``, ``i18n._``, ``i18n.translate``, ``translate``.
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _catalog_paths() -> dict:
    """Return {lang: path} for all existing catalog directories."""
    result = {}
    if not LOCALES_DIR.is_dir():
        return result
    for d in sorted(LOCALES_DIR.iterdir()):
        if d.is_dir():
            f = d / "messages.json"
            if f.exists():
                result[d.name] = f
    return result


def load_catalog(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_catalog(path: Path, data: dict) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(payload + "\n", encoding="utf-8")


def cmd_update(args) -> int:
    source = extract_strings()
    source_set = set(source)

    lang_paths = _catalog_paths()
    if args.lang:
        lang_paths = {k: v for k, v in lang_paths.items() if k == args.lang}
    if not args.all:
        # The source-language catalog is an identity mirror of the code and is
        # already provided by the English fallback, so leave it untouched.
        lang_paths = {k: v for k, v in lang_paths.items() if k != SOURCE_LANG}

    if not lang_paths:
        print("No catalogs to update (translations only). Use --all to "
              "populate the source-language catalog too.")
        return 0

    for lang, path in lang_paths.items():
        catalog = load_catalog(path)
        original = dict(catalog)

        if not args.no_remove:
            # Drop orphans (keys no longer present in the code), but keep the
            # source-language catalog clean as it mirrors the source strings.
            for key in list(catalog.keys()):
                if key not in source_set:
                    del catalog[key]

        # Add missing source strings (placeholder = source string). Never
        # overwrite an existing value (keeps real translations intact).
        for key in source:
            if key not in catalog:
                catalog[key] = key

        # Sort keys alphabetically for a stable, diff-friendly file.
        catalog = dict(sorted(catalog.items()))

        if catalog != original:
            write_catalog(path, catalog)
            added = len(catalog) - len(original)
            print(f"[update] {lang}: {len(catalog)} keys "
                  f"(diff: +{added} net)")
        else:
            print(f"[update] {lang}: up to date")

    return 0


def cmd_check(args) -> int:
    source = extract_strings()
    source_set = set(source)
    issues = []

    lang_paths = _catalog_paths()
    if args.lang:
        lang_paths = {k: v for k, v in lang_paths.items() if k == args.lang}

    if not lang_paths:
        print("No catalogs found.")
        return 1

    for lang, path in lang_paths.items():
        catalog = load_catalog(path)
        catalog_keys = set(catalog.keys())

        is_source = lang == SOURCE_LANG

        # Orphan keys (present in catalog but not in code). Checked for all
        # languages, including the source catalog.
        orphans = sorted(catalog_keys - source_set)

        if is_source:
            # The source catalog is an identity mirror: missing keys are
            # already provided by the code fallback, so nothing to report
            # except orphans that no longer exist in the code.
            missing = []
            untranslated = []
        else:
            # Missing source strings.
            missing = sorted(source_set - catalog_keys)
            # Untranslated placeholders (value == the english source).
            untranslated = sorted(
                k for k, v in catalog.items() if v == k and k in source_set
            )

        if missing:
            issues.append(f"[{lang}] missing {len(missing)}: {', '.join(missing)}")
        if orphans:
            issues.append(f"[{lang}] orphan {len(orphans)}: {', '.join(orphans)}")
        if untranslated:
            issues.append(
                f"[{lang}] untranslated {len(untranslated)}: "
                f"{', '.join(untranslated)}"
            )

    if issues:
        print("i18n check found issues:")
        for line in issues:
            print(f"  - {line}")
        return 1 if args.strict else 0

    print(f"i18n check OK: {len(source)} source strings, "
          f"{len(lang_paths)} catalog(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_update = sub.add_parser("update", help="Add missing strings to catalogs")
    p_update.add_argument("--lang", default=None, help="Restrict to one lang")
    p_update.add_argument("--no-remove", action="store_true",
                          help="Keep orphan keys instead of removing them")
    p_update.add_argument("--all", action="store_true",
                          help="Also populate the source-language catalog")
    p_update.set_defaults(func=cmd_update)

    p_check = sub.add_parser("check", help="Report catalog sync state")
    p_check.add_argument("--lang", default=None, help="Restrict to one lang")
    p_check.add_argument("--strict", action="store_true",
                         help="Exit non-zero if any issue is found")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
