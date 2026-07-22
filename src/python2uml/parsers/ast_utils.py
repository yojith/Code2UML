"""AST helpers."""

from __future__ import annotations

import ast


def is_private(name: str) -> bool:
    return name.startswith("_")


def annotation_to_str(annotation: ast.AST | None) -> str | None:
    if annotation is None:
        return None
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value
    return ast.unparse(annotation)
