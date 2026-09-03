"""Lightweight internationalization (i18n) support.

Provides a ``gettext``-style ``_()`` translation function backed by simple
JSON catalogs stored under ``mint_dynamic_theme/locales/<lang>/messages.json``.

The active language is resolved from (in order of precedence):
  1. The ``MDT_LANG`` environment variable (e.g. ``es``, ``es_AR``).
  2. The ``LANG`` / ``LC_ALL`` / ``LC_MESSAGES`` locale environment variables.
  3. The English catalog as fallback.

Loading is lazy and the resulting catalog is cached per language, so the
first ``_()`` call in a hot path reads the file at most once per language
and every later lookup is an in-memory dict access. No catalog I/O happens
at import time, which keeps application startup time unchanged. An optional
non-blocking background preload (:func:`preload_catalogs`) can warm up all
available languages so language switches at runtime are instant, without
touching the startup path.

This makes it straightforward to add support for new languages: drop a JSON
file in :file:`locales/<lang>/` mapping each source English string to its
translation and the UI will use it automatically. The ``scripts/i18n_tools.py``
script keeps these catalogs in sync with the ``_()`` strings found in the code.
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Mapping, Optional

log = logging.getLogger("mint-dynamic-theme")

LOCALES_DIR = Path(__file__).resolve().parent / "locales"

# Source language used in the UI source strings (also the fallback).
DEFAULT_LANG = "en"

# Cache: {lang: catalog_dict}
_catalogs: dict = {}

# Cache: {message: resolved_string} for the currently resolved catalog.
_string_cache: dict = {}

# Currently resolved language (used to invalidate _string_cache on switch).
_resolved_lang: Optional[str] = None

_lock = threading.RLock()

# Track available languages for optional background preload.
_available_langs: list = []


def _normalize(lang: str) -> str:
    """Normalize a locale string like ``es_AR.UTF-8`` to ``es_AR`` / ``es``."""
    lang = lang.strip()
    if not lang:
        return ""
    # Strip any charset suffix (e.g. en_US.UTF-8 -> en_US)
    lang = lang.split(".")[0]
    # Replace regional separator (es_AR) with the underscore used by catalogs
    return lang.replace("-", "_")


def _candidate_langs() -> list:
    """Return the ordered list of candidate locale codes."""
    explicit = os.getenv("MDT_LANG", "").strip()
    if explicit:
        return [_normalize(explicit)]

    candidates = []
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.getenv(var, "").strip()
        if val:
            candidates.append(_normalize(val))
    return [c for c in candidates if c] or [DEFAULT_LANG]


def _load_catalog(lang: str) -> dict:
    """Load a JSON catalog for a language (best effort, no cache)."""
    catalog_path = LOCALES_DIR / lang / "messages.json"
    try:
        if catalog_path.exists():
            return json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        log.debug("Could not load catalog %s: %s", catalog_path, e)
    return {}


def available_languages() -> list:
    """Return the list of locale codes with a catalog on disk."""
    global _available_langs
    if not _available_langs:
        with _lock:
            if not _available_langs:
                try:
                    _available_langs = sorted(
                        d.name
                        for d in LOCALES_DIR.iterdir()
                        if d.is_dir() and (d / "messages.json").exists()
                    )
                except OSError:
                    _available_langs = []
    return _available_langs


def _resolve_catalog(lang: str) -> dict:
    """Return the cached catalog for ``lang``, falling back from regional to
    base language, and finally to the English source strings."""
    normalized = _normalize(lang)
    if normalized == DEFAULT_LANG:
        return {}

    with _lock:
        cached = _catalogs.get(normalized)
        if cached is not None:
            return cached

        catalog = {}
        if "_" in normalized:
            base = normalized.split("_", 1)[0]
            catalog = _load_catalog(normalized)
            if not catalog and base != normalized:
                catalog = _load_catalog(base)
        else:
            catalog = _load_catalog(normalized)

        _catalogs[normalized] = catalog
        return catalog


def translate(message: str, lang: Optional[str] = None, **kwargs) -> str:
    """Translate ``message`` to the active language, applying ``kwargs`` as
    format arguments if provided.

    Falls back to the original string when no translation is available.
    """
    if lang is None:
        lang = _candidate_langs()[0]
    normalized = _normalize(lang)

    global _resolved_lang
    with _lock:
        if normalized != _resolved_lang:
            _string_cache.clear()
            _resolved_lang = normalized

        result = _string_cache.get(message)
        if result is None:
            catalog = _resolve_catalog(normalized)
            result = catalog.get(message, message)
            _string_cache[message] = result

    if kwargs:
        try:
            return result.format(**kwargs)
        except (KeyError, IndexError):
            return result
    return result


def preload_catalogs(blocking: bool = False) -> None:
    """Warm up the catalogs for all available languages.

    By default this runs on a low-priority background thread so it never
    adds latency to the application startup path. Set ``blocking=True`` to
    wait for completion (useful for tests or non-GUI contexts).
    """
    langs = available_languages()

    def _warm():
        for lang in langs:
            if lang != DEFAULT_LANG and _normalize(lang) not in _catalogs:
                try:
                    _resolve_catalog(lang)
                except Exception as e:
                    log.debug("Preload failed for %s: %s", lang, e)

    if blocking:
        _warm()
        return

    try:
        t = threading.Thread(target=_warm, daemon=True, name="mdt-i18n-preload")
        t.start()
    except Exception:
        # If a thread cannot be spawned, preload synchronously is not worth
        # blocking the caller; just skip the background warm-up.
        pass


def current_lang() -> str:
    """Return the active language code (first candidate)."""
    return _candidate_langs()[0]


# gettext-style alias
_ = translate
