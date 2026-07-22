"""UML class model."""

from __future__ import annotations

from dataclasses import dataclass, field

from python2uml.model.enums import ClassKind
from python2uml.model.uml_attribute import UMLAttribute
from python2uml.model.uml_method import UMLMethod


@dataclass(slots=True)
class UMLClass:
    name: str
    kind: ClassKind = ClassKind.CLASS
    attributes: list[UMLAttribute] = field(default_factory=list)
    methods: list[UMLMethod] = field(default_factory=list)
