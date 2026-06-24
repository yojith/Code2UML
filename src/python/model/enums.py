"""Domain enums."""

from __future__ import annotations

from enum import Enum


class Visibility(str, Enum):
    PUBLIC = "+"
    PROTECTED = "#"
    PRIVATE = "-"


class RelationshipType(str, Enum):
    INHERITANCE = "inheritance"
    ASSOCIATION = "association"
    AGGREGATION = "aggregation"
    COMPOSITION = "composition"

