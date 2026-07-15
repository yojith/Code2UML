"""Language parser registration and dispatch."""

from __future__ import annotations

from model.enums import ProjectLanguage
from parser.cpp_parser import CppParser
from parser.java_parser import JavaParser
from parser.normalized_ast import NormalizedModule
from parser.python_parser import PythonParser

PARSERS = {ProjectLanguage.PYTHON: PythonParser, ProjectLanguage.JAVA: JavaParser, ProjectLanguage.CPP: CppParser}


class AbstractSyntaxTreeLoader:
    def load(self, *args) -> list[NormalizedModule]:
        language = ProjectLanguage.PYTHON
        paths = args
        if args and isinstance(args[0], ProjectLanguage):
            language = args[0]
            paths = args[1:]
        return PARSERS[language]().parse(*paths)
