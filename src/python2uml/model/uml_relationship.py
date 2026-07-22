"""UML relationship model."""

from __future__ import annotations

from dataclasses import dataclass

from model.enums import RelationshipType


@dataclass(frozen=True, slots=True)
class UMLRelationship:
    source: str
    target: str
    relationship_type: RelationshipType
