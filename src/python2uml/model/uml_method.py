"""UML method model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class UMLMethod:
    name: str
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    visibility: str = "+"
