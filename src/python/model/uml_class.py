"""UML class model."""

from __future__ import annotations

from dataclasses import dataclass, field

from model.uml_attribute import UMLAttribute
from model.uml_method import UMLMethod


@dataclass(slots=True)
class UMLClass:
    name: str
    attributes: list[UMLAttribute] = field(default_factory=list)
    methods: list[UMLMethod] = field(default_factory=list)
