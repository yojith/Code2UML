from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
PYTHON_SRC = ROOT / "src" / "python"
if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from model.enums import ProjectLanguage
from parser.project_loader import ProjectLoader
from generator import UMLGenerator
from render.graphviz_renderer import GraphvizRenderer
from model.uml_diagram import UMLDiagram
from parser.abstracter import AbstractSyntaxTreeLoader
from analyzers.class_analyzer import ClassAnalyzer
from analyzers.relationship_analyzer import RelationshipAnalyzer
from model.enums import RelationshipType


class ProjectLoaderTests(TestCase):
    def test_collect_source_files_uses_project_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pkg").mkdir()
            (root / "main.py").write_text("class A:\n    pass\n", encoding="utf-8")
            (root / "pkg" / "Main.java").write_text("class Main {}", encoding="utf-8")
            (root / "pkg" / "notes.txt").write_text("ignore", encoding="utf-8")

            loader = ProjectLoader()

            python_files = loader.collect_source_files(ProjectLanguage.PYTHON, str(root))
            java_files = loader.collect_source_files(ProjectLanguage.JAVA, str(root))

            self.assertEqual([str(root / "main.py")], python_files)
            self.assertEqual([str(root / "pkg" / "Main.java")], java_files)


class GraphvizRendererTests(TestCase):
    def test_render_fails_when_dot_is_missing(self) -> None:
        with patch("render.graphviz_renderer.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError) as exc_info:
                GraphvizRenderer().render(UMLDiagram(), "out.svg")

        self.assertIn("dot", str(exc_info.exception))
        self.assertIn("Install Graphviz", str(exc_info.exception))


class UMLGeneratorTests(TestCase):
    def test_java_project_type_reaches_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "Main.java"
            source.write_text("class Main {}", encoding="utf-8")

            with patch.object(GraphvizRenderer, "render") as render_mock:
                UMLGenerator(renderer=GraphvizRenderer()).generate(
                    ProjectLanguage.JAVA,
                    "out.svg",
                    str(source),
                )

            render_mock.assert_called_once()


class NormalizedAnalyzerTests(TestCase):
    def test_python_normalized_pipeline_keeps_relationships(self) -> None:
        loader = AbstractSyntaxTreeLoader()
        modules = loader.load(str(ROOT / "src" / "test" / "example3.py"))

        diagram = ClassAnalyzer().analyze(modules)
        RelationshipAnalyzer().analyze(modules, diagram)

        self.assertEqual({"Entity", "User", "Admin", "Profile", "Department"}, set(diagram.classes))
        relationships = {(relationship.source, relationship.target, relationship.relationship_type) for relationship in diagram.relationships}
        self.assertIn(("User", "Entity", RelationshipType.INHERITANCE), relationships)
        self.assertIn(("Admin", "User", RelationshipType.INHERITANCE), relationships)
        self.assertIn(("User", "Profile", RelationshipType.COMPOSITION), relationships)
        self.assertIn(("Department", "User", RelationshipType.AGGREGATION), relationships)

    def test_java_loader_normalizes_relationship_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "User.java"
            source.write_text(
                """
class Entity {}
class Profile {}
class Department {}
class User extends Entity {
    private Profile profile;
    public User() {
        this.profile = new Profile();
    }
    public void assign() {
        Department department = new Department();
    }
}
""",
                encoding="utf-8",
            )

            modules = AbstractSyntaxTreeLoader().load(ProjectLanguage.JAVA, str(source))
            diagram = ClassAnalyzer().analyze(modules)
            RelationshipAnalyzer().analyze(modules, diagram)
            relationships = {(relationship.source, relationship.target, relationship.relationship_type) for relationship in diagram.relationships}

            self.assertIn(("User", "Entity", RelationshipType.INHERITANCE), relationships)
            self.assertIn(("User", "Profile", RelationshipType.COMPOSITION), relationships)
            self.assertIn(("User", "Department", RelationshipType.ASSOCIATION), relationships)

    def test_cpp_loader_normalizes_relationship_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "user.hpp"
            source.write_text(
                """
class Entity {};
class Profile {};
class Department {};
class User : public Entity {
private:
    Profile profile;
public:
    User() {
        this->profile = Profile();
    }
    void assign(Department department) {
        Department local_department;
    }
};
""",
                encoding="utf-8",
            )

            modules = AbstractSyntaxTreeLoader().load(ProjectLanguage.CPP, str(source))
            diagram = ClassAnalyzer().analyze(modules)
            RelationshipAnalyzer().analyze(modules, diagram)
            relationships = {(relationship.source, relationship.target, relationship.relationship_type) for relationship in diagram.relationships}

            self.assertIn(("User", "Entity", RelationshipType.INHERITANCE), relationships)
            self.assertIn(("User", "Profile", RelationshipType.COMPOSITION), relationships)
            self.assertIn(("User", "Department", RelationshipType.ASSOCIATION), relationships)

    def test_c_loader_normalizes_structs_and_methods(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            header = Path(tmpdir) / "user.h"
            impl = Path(tmpdir) / "user.c"
            header.write_text(
                """
struct Profile {};
struct Department {};
struct User {
    struct Profile profile;
};
""",
                encoding="utf-8",
            )
            impl.write_text(
                """
#include "user.h"
void assign_user(struct User* self, struct Department department) {
    struct Department local_department;
}
""",
                encoding="utf-8",
            )

            modules = AbstractSyntaxTreeLoader().load(ProjectLanguage.C, str(header), str(impl))
            diagram = ClassAnalyzer().analyze(modules)
            RelationshipAnalyzer().analyze(modules, diagram)
            relationships = {(relationship.source, relationship.target, relationship.relationship_type) for relationship in diagram.relationships}

            self.assertIn(("User", "Profile", RelationshipType.COMPOSITION), relationships)
            self.assertIn(("User", "Department", RelationshipType.ASSOCIATION), relationships)
