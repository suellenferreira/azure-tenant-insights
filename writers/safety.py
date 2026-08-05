"""Output-safety helpers for externally supplied Azure inventory data."""

from __future__ import annotations

import html
from typing import Any


_FORMULA_PREFIXES = ("=", "+", "-", "@")


def html_escape(value: Any) -> str:
    """Return a string safe for insertion in HTML text or quoted attributes.

    ``unescape`` makes repeated use idempotent when a renderer additionally
    escapes an individual value.
    """
    return html.escape(html.unescape(str(value if value is not None else "")), quote=True)


def html_safe_data(value: Any) -> Any:
    """Recursively escape strings in Azure-derived data before HTML rendering."""
    if isinstance(value, dict):
        return {key: html_safe_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [html_safe_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(html_safe_data(item) for item in value)
    if isinstance(value, str):
        return html_escape(value)
    return value


def excel_safe_data(value: Any) -> Any:
    """Neutralize formula-looking strings throughout Excel-bound inventory data."""
    if isinstance(value, dict):
        return {key: excel_safe_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [excel_safe_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(excel_safe_data(item) for item in value)
    if isinstance(value, str) and value.lstrip().startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value
