"""UML attribute model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UMLAttribute:
    name: str
    type_name: str | None = None
    visibility: str = "+"
