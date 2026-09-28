"""Internationalization (i18n) module.

Loads translation dictionaries from app/translations/*.json and provides
a `t(key, lang)` function that resolves dotted keys like "nav.hotels".

Language resolution order (in order of priority):
1. Explicit `lang` parameter (URL query ?lang=ar)
2. Cookie "px_lang"
3. Accept-Language header
4. DEFAULT_LANGUAGE (en)
"""

import json
from functools import lru_cache
from pathlib import Path

from starlette.requests import Request

BASE_DIR = Path(__file__).resolve().parent.parent
TRANSLATIONS_DIR = BASE_DIR / "translations"

SUPPORTED_LANGUAGES = ["en", "ar", "fil", "hi"]
DEFAULT_LANGUAGE = "en"
RTL_LANGUAGES = {"ar"}


@lru_cache(maxsize=16)
def load_translations(lang: str) -> dict:
    """Load translation dictionary for a language. Cached."""
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    path = TRANSLATIONS_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _lookup(dictionary: dict, dotted_key: str) -> str | None:
    """Resolve a dotted key like 'nav.hotels' inside a nested dict."""
    parts = dotted_key.split(".")
    node = dictionary
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node if isinstance(node, str) else None


def translate(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Return the translation for a key, falling back to English, then key.

    Supports named placeholders: t("home.hero_eyebrow", count=21).
    """
    lang_translations = load_translations(lang)
    result = _lookup(lang_translations, key)
    if result is None and lang != DEFAULT_LANGUAGE:
        en_translations = load_translations(DEFAULT_LANGUAGE)
        result = _lookup(en_translations, key)
    if result is None:
        result = key

    if kwargs:
        try:
            return result.format(**kwargs)
        except (KeyError, ValueError):
            return result
    return result


def resolve_language(request: Request) -> str:
    """Determine the current language for a request."""
    # 1. Explicit ?lang=xx
    lang = request.query_params.get("lang")
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # 2. Cookie
    lang = request.cookies.get("px_lang")
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # 3. Accept-Language header (first match)
    header = request.headers.get("accept-language", "")
    if header:
        for candidate in header.split(","):
            code = candidate.split(";")[0].strip().lower()
            # Take the first 2 chars (e.g. "ar-EG" -> "ar")
            short = code[:2]
            if short in SUPPORTED_LANGUAGES:
                return short

    # 4. Default
    return DEFAULT_LANGUAGE


def is_rtl(lang: str) -> bool:
    """Return True if the language is right-to-left."""
    return lang in RTL_LANGUAGES
