"""UML diagram aggregate model."""

from __future__ import annotations

from dataclasses import dataclass, field

from model.uml_class import UMLClass
from model.uml_relationship import UMLRelationship


@dataclass(slots=True)
class UMLDiagram:
    classes: dict[str, UMLClass] = field(default_factory=dict)
    relationships: list[UMLRelationship] = field(default_factory=list)
