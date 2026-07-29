"""High-level UML generation orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from python2uml.analyzers.class_analyzer import ClassAnalyzer
from python2uml.analyzers.relationship_analyzer import RelationshipAnalyzer
from python2uml.model.enums import ProjectLanguage
from python2uml.model.uml_diagram import UMLDiagram
from python2uml.parsers.abstracter import AbstractSyntaxTreeLoader
from python2uml.parsers.normalized_ast import SourceDiagnostic
from python2uml.parsers.project_loader import ProjectLoader
from python2uml.renderers.drawio_renderer import DrawioRenderer
from python2uml.renderers.graphviz_renderer import GraphvizRenderer


@dataclass(slots=True)
class AnalysisResult:
    diagram: UMLDiagram
    diagnostics: list[SourceDiagnostic]
    source_files: list[str]


class UMLGenerator:
    def __init__(
        self,
        project_loader: ProjectLoader | None = None,
        ast_loader: AbstractSyntaxTreeLoader | None = None,
        class_analyzer: ClassAnalyzer | None = None,
        relationship_analyzer: RelationshipAnalyzer | None = None,
        renderer: GraphvizRenderer | DrawioRenderer | None = None,
    ) -> None:
        self.project_loader = project_loader or ProjectLoader()
        self.ast_loader = ast_loader or AbstractSyntaxTreeLoader()
        self.class_analyzer = class_analyzer or ClassAnalyzer()
        self.relationship_analyzer = relationship_analyzer or RelationshipAnalyzer()
        self.renderer = renderer or GraphvizRenderer()

    def analyze(self, project_type: ProjectLanguage, *paths: str) -> AnalysisResult:
        filepaths = self.project_loader.collect_source_files(project_type, *paths)
        documents = self.ast_loader.load(project_type, *filepaths)
        diagram = self.class_analyzer.analyze(documents)
        self.relationship_analyzer.analyze(documents, diagram)
        if not diagram.classes:
            raise RuntimeError("No UML classes could be analyzed from the selected source files.")
        return AnalysisResult(diagram, [diagnostic for document in documents for diagnostic in document.diagnostics], filepaths)

    def generate(self, project_type: ProjectLanguage, output: str, *paths: str) -> AnalysisResult:
        result = self.analyze(project_type, *paths)
        self.renderer.render(result.diagram, output)
        return result


def generate_uml_from_files(project_type: ProjectLanguage, output: str, *paths: str) -> AnalysisResult:
    renderer = DrawioRenderer() if output.lower().endswith(".drawio") else GraphvizRenderer()
    return UMLGenerator(renderer=renderer).generate(project_type, output, *paths)
