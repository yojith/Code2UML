from __future__ import annotations

import json
from pathlib import Path

from generator import AnalysisResult, UMLGenerator
from main import main
from model.enums import ProjectLanguage


def write_partially_invalid_source(tmp_path: Path) -> Path:
    source = tmp_path / "Partial.java"
    source.write_text("public class Valid { int value; }\npublic class Broken { void broken( }\n", encoding="utf-8")
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

    monkeypatch.setattr("generator.GraphvizRenderer.render", render)

    exit_code = main(["-t", "java", "-o", str(output), "-p", str(source)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert set(payload) == {"output", "classes", "relationships", "diagnostics"}
    assert payload["output"] == str(output)
    assert payload["classes"]["Valid"] == {
        "name": "Valid",
        "kind": "class",
        "attributes": [{"name": "value", "type_name": "int", "visibility": "+"}],
        "methods": [],
    }
    assert payload["relationships"] == []
    assert payload["diagnostics"][0]["path"] == str(source)
    assert output.exists()


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

    monkeypatch.setattr("generator.GraphvizRenderer.render", fail_render)

    exit_code = main(["-t", "java", "-o", str(tmp_path / "preview.svg"), "-p", str(source)])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert captured.out == ""
    assert captured.err == "render failed\n"
