"""Language parser registration and dispatch."""

from __future__ import annotations

from python2uml.model.enums import ProjectLanguage
from python2uml.parsers.c_parser import CParser
from python2uml.parsers.cpp_parser import CppParser
from python2uml.parsers.java_parser import JavaParser
from python2uml.parsers.normalized_ast import NormalizedModule
from python2uml.parsers.python_parser import PythonParser

PARSERS = {ProjectLanguage.PYTHON: PythonParser, ProjectLanguage.JAVA: JavaParser, ProjectLanguage.CPP: CppParser, ProjectLanguage.C: CParser}


class AbstractSyntaxTreeLoader:
    def load(self, *args) -> list[NormalizedModule]:
        language = ProjectLanguage.PYTHON
        paths = args
        if args and isinstance(args[0], ProjectLanguage):
            language = args[0]
            paths = args[1:]
        return PARSERS[language]().parse(*paths)
