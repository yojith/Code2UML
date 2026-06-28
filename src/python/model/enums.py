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


class ClassKind(str, Enum):
    CLASS = "class"
    ABSTRACT_CLASS = "abstract_class"
    INTERFACE = "interface"
    ENUM = "enum"
    STRUCT = "struct"
    FILE = "file"
    MODULE = "module"


class ProjectLanguage(str, Enum):
    PYTHON = "python"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
