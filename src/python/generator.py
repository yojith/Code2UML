"""High-level UML generation orchestration."""

from __future__ import annotations

from analyzers.class_analyzer import ClassAnalyzer
from analyzers.relationship_analyzer import RelationshipAnalyzer
from parser.abstracter import AbstractSyntaxTreeLoader
from parser.project_loader import ProjectLoader
from render.graphviz_renderer import GraphvizRenderer


class UMLGenerator:
    def __init__(
        self,
        project_loader: ProjectLoader | None = None,
        ast_loader: AbstractSyntaxTreeLoader | None = None,
        class_analyzer: ClassAnalyzer | None = None,
        relationship_analyzer: RelationshipAnalyzer | None = None,
        renderer: GraphvizRenderer | None = None,
    ) -> None:
        self.project_loader = project_loader or ProjectLoader()
        self.ast_loader = ast_loader or AbstractSyntaxTreeLoader()
        self.class_analyzer = class_analyzer or ClassAnalyzer()
        self.relationship_analyzer = relationship_analyzer or RelationshipAnalyzer()
        self.renderer = renderer or GraphvizRenderer()

    def generate(self, output: str, *paths: str) -> None:
        filepaths = self.project_loader.collect_python_files(*paths)
        ast_trees = self.ast_loader.load(*filepaths)
        diagram = self.class_analyzer.analyze(ast_trees)
        self.relationship_analyzer.analyze(ast_trees, diagram)
        self.renderer.render(diagram, output)


def generate_uml_from_files(output: str, *paths: str) -> None:
    UMLGenerator().generate(output, *paths)
