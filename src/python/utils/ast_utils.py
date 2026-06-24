"""AST helpers."""

from __future__ import annotations

import ast


def is_private(name: str) -> bool:
    return name.startswith("_")


def annotation_to_str(annotation: ast.AST | None) -> str | None:
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Constant) and annotation.value is not None:
        return str(annotation.value)
    return None

