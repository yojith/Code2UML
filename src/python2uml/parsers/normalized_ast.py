"""Language-agnostic normalized AST models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from python2uml.model.enums import ClassKind


@dataclass(slots=True)
class SourceDiagnostic:
    path: str
    line: int
    column: int
    severity: str
    message: str


@dataclass(slots=True)
class NormalizedTypeReference:
    type_name: str
    context: Literal["parameter", "return", "local", "include"]


@dataclass(slots=True)
class NormalizedMemberAssignment:
    member_name: str
    type_name: str
    ownership: Literal["constructed", "supplied", "value", "reference"]


@dataclass(slots=True)
class NormalizedParameter:
    name: str
    type_name: str | None = None


@dataclass(slots=True)
class NormalizedAttribute:
    name: str
    type_name: str | None = None
    visibility: str = "+"
    is_static: bool = False


@dataclass(slots=True)
class NormalizedLocalInstantiation:
    class_name: str
    assigned_name: str | None = None
    assigned_attribute: str | None = None


@dataclass(slots=True)
class NormalizedAppendCall:
    collection_attribute: str
    item_name: str | None = None
    item_type: str | None = None


@dataclass(slots=True)
class NormalizedMethod:
    name: str
    visibility: str = "+"
    is_constructor: bool = False
    is_abstract: bool = False
    is_pure_virtual: bool = False
    is_static: bool = False
    parameters: list[NormalizedParameter] = field(default_factory=list)
    return_type: str | None = None
    local_instantiations: list[NormalizedLocalInstantiation] = field(default_factory=list)
    append_calls: list[NormalizedAppendCall] = field(default_factory=list)


@dataclass(slots=True)
class NormalizedClass:
    name: str
    kind: ClassKind = ClassKind.CLASS
    parent: str | None = None
    bases: list[str] = field(default_factory=list)
    attributes: list[NormalizedAttribute] = field(default_factory=list)
    methods: list[NormalizedMethod] = field(default_factory=list)
    composed_types: set[str] = field(default_factory=set)
    member_assignments: list[NormalizedMemberAssignment] = field(default_factory=list)
    type_references: list[NormalizedTypeReference] = field(default_factory=list)


@dataclass(slots=True)
class NormalizedModule:
    path: str
    classes: list[NormalizedClass] = field(default_factory=list)
    diagnostics: list[SourceDiagnostic] = field(default_factory=list)
