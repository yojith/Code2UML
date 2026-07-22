"""Type resolution helpers."""

from __future__ import annotations


def normalize_type_name(type_name: str | None) -> str | None:
    return type_name.strip() if isinstance(type_name, str) else None
