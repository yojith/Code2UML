"""Language parser registration and dispatch."""

from __future__ import annotations

from model.enums import ProjectLanguage
from parser.normalized_ast import NormalizedModule
from parser.python_parser import PythonParser

PARSERS = {ProjectLanguage.PYTHON: PythonParser}


class AbstractSyntaxTreeLoader:
    def load(self, language: ProjectLanguage, *paths: str) -> list[NormalizedModule]:
        return PARSERS[language]().parse(*paths)
