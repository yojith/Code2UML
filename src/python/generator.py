"""High-level UML generation orchestration."""

from __future__ import annotations

from analyzers.class_analyzer import ClassAnalyzer
from analyzers.relationship_analyzer import RelationshipAnalyzer
from model.enums import ProjectLanguage
from parser.abstracter import AbstractSyntaxTreeLoader
from parser.project_loader import ProjectLoader
from render.drawio_renderer import DrawioRenderer
from render.graphviz_renderer import GraphvizRenderer


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

    def generate(self, project_type: ProjectLanguage, output: str, *paths: str) -> None:
        filepaths = self.project_loader.collect_source_files(project_type, *paths)
        documents = self.ast_loader.load(project_type, *filepaths)
        diagram = self.class_analyzer.analyze(documents)
        self.relationship_analyzer.analyze(documents, diagram)
        self.renderer.render(diagram, output)


def generate_uml_from_files(project_type: ProjectLanguage, output: str, *paths: str) -> None:
    renderer = DrawioRenderer() if output.lower().endswith(".drawio") else GraphvizRenderer()
    UMLGenerator(renderer=renderer).generate(project_type, output, *paths)
