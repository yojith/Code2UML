from __future__ import annotations

import json
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from python2uml.cli import main
from python2uml.generator import AnalysisResult, UMLGenerator
from python2uml.model.enums import ProjectLanguage


def test_installed_package_exposes_python2uml_console_script():
    matches = [entry for entry in entry_points(group="console_scripts") if entry.name == "python2uml"]
    assert [entry.value for entry in matches] == ["python2uml.cli:main"]


def write_partially_invalid_source(tmp_path: Path) -> Path:
    source = tmp_path / "Partial.java"
    source.write_text("public class Valid { int value; }\nclass Broken { # }\n", encoding="utf-8")
    return source


class RecordingRenderer:
    def __init__(self) -> None:
        self.diagram = None
        self.output = None

    def render(self, diagram, output: str) -> None:
        self.diagram = diagram
        self.output = output


def test_generator_returns_partial_analysis_and_the_rendered_result(tmp_path):
    source = write_partially_invalid_source(tmp_path)
    output = str(tmp_path / "preview.svg")
    renderer = RecordingRenderer()

    analyzed = UMLGenerator(renderer=renderer).analyze(ProjectLanguage.JAVA, str(source))
    rendered = UMLGenerator(renderer=renderer).generate(ProjectLanguage.JAVA, output, str(source))

    assert isinstance(analyzed, AnalysisResult)
    assert "Valid" in analyzed.diagram.classes
    assert analyzed.diagnostics[0].path == str(source)
    assert renderer.diagram is rendered.diagram
    assert renderer.output == output
    assert rendered.diagnostics[0].path == str(source)


def test_cli_renders_valid_declarations_and_reports_source_errors(tmp_path, capsys, monkeypatch):
    source = write_partially_invalid_source(tmp_path)
    output = tmp_path / "preview.svg"

    def render(self, diagram, output_path):
        Path(output_path).write_text("<svg/>", encoding="utf-8")

    monkeypatch.setattr("python2uml.generator.GraphvizRenderer.render", render)

    exit_code = main(["-t", "java", "-o", str(output), "-p", str(source)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert set(payload) == {"output", "classes", "relationships", "diagnostics", "documents"}
    assert payload["output"] == str(output)
    assert payload["classes"]["Valid"] == {
        "name": "Valid",
        "kind": "class",
        "attributes": [{"name": "value", "type_name": "int", "visibility": "+"}],
        "methods": [],
    }
    assert payload["relationships"] == []
    expected_diagnostic = {"path": str(source), "line": 2, "column": 16, "severity": "error", "message": "unexpected syntax"}
    assert payload["diagnostics"] == [expected_diagnostic, expected_diagnostic]
    assert all({name: type(value) for name, value in diagnostic.items()} == {"path": str, "line": int, "column": int, "severity": str, "message": str} for diagnostic in payload["diagnostics"])
    assert output.exists()


def test_cli_reports_analyzed_documents_in_collection_order(tmp_path, capsys, monkeypatch):
    first = tmp_path / "a_model.py"
    second = tmp_path / "b_model.py"
    first.write_text("class First:\n    pass\n", encoding="utf-8")
    second.write_text("class Second:\n    pass\n", encoding="utf-8")

    monkeypatch.setattr("python2uml.generator.GraphvizRenderer.render", lambda self, diagram, output_path: None)

    exit_code = main(["-t", "python", "-o", str(tmp_path / "preview.svg"), "-p", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["documents"] == [str(first), str(second)]


@pytest.mark.parametrize(
    "language,filename,source,expected_class",
    [
        ("python", "model.py", "class PythonModel:\n    pass\n", "PythonModel"),
        ("java", "Model.java", "class JavaModel {}\n", "JavaModel"),
        ("cpp", "model.cpp", "class CppModel {};\n", "CppModel"),
        ("c", "model.c", "struct CModel { int value; };\n", "CModel"),
    ],
)
def test_cli_dispatches_all_project_languages(tmp_path, capsys, monkeypatch, language, filename, source, expected_class):
    source_path = tmp_path / filename
    source_path.write_text(source, encoding="utf-8")
    output = tmp_path / "preview.svg"

    def render(self, diagram, output_path):
        Path(output_path).write_text("<svg/>", encoding="utf-8")

    monkeypatch.setattr("python2uml.generator.GraphvizRenderer.render", render)

    exit_code = main(["-t", language, "-o", str(output), "-p", str(source_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert expected_class in payload["classes"]
    assert payload["output"] == str(output)


def test_cli_reports_drawio_layout_failure_on_stderr(tmp_path, capsys, monkeypatch):
    source = tmp_path / "model.py"
    source.write_text("class Model:\n    pass\n", encoding="utf-8")
    output = tmp_path / "preview.drawio"
    error = "Graphviz draw.io layout failed: Graphviz dot.exe was not found on PATH."

    def fail_layout(self, dot_source):
        raise RuntimeError(error)

    monkeypatch.setattr("python2uml.renderers.drawio_renderer.DrawioRenderer._run_layout", fail_layout)

    exit_code = main(["-t", "python", "-o", str(output), "-p", str(source)])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert captured.out == ""
    assert captured.err == f"{error}\n"


def test_cli_serializes_relationship_enum_as_primitive_value(tmp_path, capsys, monkeypatch):
    source = tmp_path / "model.py"
    source.write_text("class Product:\n    pass\n\nclass Cart:\n    def add(self, product: Product):\n        pass\n", encoding="utf-8")

    monkeypatch.setattr("python2uml.generator.GraphvizRenderer.render", lambda self, diagram, output_path: None)

    exit_code = main(["-t", "python", "-o", str(tmp_path / "preview.svg"), "-p", str(source)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert payload["relationships"] == [{"source": "Cart", "target": "Product", "relationship_type": "association"}]
    assert type(payload["relationships"][0]["relationship_type"]) is str


def test_cli_reports_analysis_failure_on_stderr(tmp_path, capsys):
    source = tmp_path / "Empty.java"
    source.write_text("", encoding="utf-8")

    exit_code = main(["-t", "java", "-o", str(tmp_path / "preview.svg"), "-p", str(source)])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert captured.out == ""
    assert "No UML classes" in captured.err


def test_cli_reports_render_failure_on_stderr(tmp_path, capsys, monkeypatch):
    source = write_partially_invalid_source(tmp_path)

    def fail_render(self, diagram, output_path):
        raise OSError("render failed")

    monkeypatch.setattr("python2uml.generator.GraphvizRenderer.render", fail_render)

    exit_code = main(["-t", "java", "-o", str(tmp_path / "preview.svg"), "-p", str(source)])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert captured.out == ""
    assert captured.err == "render failed\n"
