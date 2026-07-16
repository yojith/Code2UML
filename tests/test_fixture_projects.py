from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from analyzers.class_analyzer import ClassAnalyzer
from analyzers.relationship_analyzer import RelationshipAnalyzer
from model.enums import ProjectLanguage
from parser.abstracter import AbstractSyntaxTreeLoader
from parser.project_loader import ProjectLoader

ROOT = Path(__file__).resolve().parent.parent


CASES = [
    (
        "python",
        "project1",
        {
            "classes": [("Cart", "class"), ("Product", "class")],
            "relationships": [("Cart", "Product", "aggregation")],
            "diagnostics": [],
        },
    ),
    (
        "python",
        "project2",
        {
            "classes": [
                ("Entity", "abstract_class"),
                ("Profile", "class"),
                ("Repository", "interface"),
                ("Settings", "class"),
                ("Team", "class"),
                ("User", "class"),
            ],
            "relationships": [
                ("Repository", "Entity", "association"),
                ("Team", "Profile", "association"),
                ("Team", "Repository", "association"),
                ("Team", "User", "aggregation"),
                ("User", "Entity", "inheritance"),
                ("User", "Profile", "composition"),
                ("User", "Repository", "implementation"),
                ("User", "Settings", "composition"),
            ],
            "diagnostics": [],
        },
    ),
    (
        "java",
        "project1",
        {
            "classes": [("Cart", "class"), ("Product", "class")],
            "relationships": [("Cart", "Product", "aggregation")],
            "diagnostics": [],
        },
    ),
    (
        "java",
        "project2",
        {
            "classes": [
                ("Entity", "abstract_class"),
                ("Profile", "class"),
                ("Repository", "interface"),
                ("Settings", "class"),
                ("Team", "class"),
                ("User", "class"),
            ],
            "relationships": [
                ("Repository", "Entity", "association"),
                ("Team", "Profile", "association"),
                ("Team", "Repository", "association"),
                ("Team", "User", "aggregation"),
                ("User", "Entity", "association"),
                ("User", "Entity", "inheritance"),
                ("User", "Profile", "composition"),
                ("User", "Repository", "implementation"),
                ("User", "Settings", "composition"),
            ],
            "diagnostics": [],
        },
    ),
    (
        "cpp",
        "project1",
        {
            "classes": [("Cart", "class"), ("Product", "struct")],
            "relationships": [("Cart", "Product", "aggregation")],
            "diagnostics": [],
        },
    ),
    (
        "cpp",
        "project2",
        {
            "classes": [
                ("Entity", "abstract_class"),
                ("Profile", "struct"),
                ("Repository", "interface"),
                ("Settings", "struct"),
                ("Team", "class"),
                ("User", "class"),
            ],
            "relationships": [
                ("Repository", "Entity", "association"),
                ("Team", "Profile", "association"),
                ("Team", "Repository", "association"),
                ("Team", "User", "aggregation"),
                ("User", "Entity", "association"),
                ("User", "Entity", "inheritance"),
                ("User", "Profile", "composition"),
                ("User", "Repository", "implementation"),
                ("User", "Settings", "composition"),
            ],
            "diagnostics": [],
        },
    ),
    (
        "c",
        "project1",
        {
            "classes": [("Cart", "struct"), ("Product", "struct"), ("shop_c", "class"), ("shop_h", "class")],
            "relationships": [
                ("Cart", "Product", "aggregation"),
                ("shop_c", "shop_h", "association"),
                ("shop_h", "Cart", "composition"),
                ("shop_h", "Product", "composition"),
            ],
            "diagnostics": [],
        },
    ),
    (
        "c",
        "project2",
        {
            "classes": [
                ("Entity", "struct"),
                ("Profile", "struct"),
                ("Team", "struct"),
                ("User", "struct"),
                ("domain_c", "class"),
                ("domain_h", "class"),
            ],
            "relationships": [
                ("Team", "Entity", "association"),
                ("Team", "Profile", "association"),
                ("Team", "User", "aggregation"),
                ("User", "Entity", "composition"),
                ("User", "Profile", "composition"),
                ("domain_c", "domain_h", "association"),
                ("domain_h", "Entity", "composition"),
                ("domain_h", "Profile", "composition"),
                ("domain_h", "Team", "composition"),
                ("domain_h", "User", "composition"),
            ],
            "diagnostics": [],
        },
    ),
]


def summarize_classes(diagram):
    return sorted((name, uml_class.kind.value) for name, uml_class in diagram.classes.items())


def summarize_relationships(diagram):
    return sorted((item.source, item.target, item.relationship_type.value) for item in diagram.relationships)


def summarize_diagnostics(modules):
    return sorted((item.path, item.line, item.column, item.severity, item.message) for module in modules for item in module.diagnostics)


@pytest.mark.parametrize("language,project,expected", CASES)
def test_fixture_project(language, project, expected):
    project_language = ProjectLanguage(language)
    root = ROOT / "src" / "test" / language / project
    files = ProjectLoader().collect_source_files(project_language, str(root))
    modules = AbstractSyntaxTreeLoader().load(project_language, *files)
    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)

    assert summarize_classes(diagram) == expected["classes"]
    assert summarize_relationships(diagram) == expected["relationships"]
    assert summarize_diagnostics(modules) == expected["diagnostics"]


def test_manual_inspector_accepts_language_and_prints_diagnostics():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "src" / "python" / "analyze_test_projects.py"),
            "--language",
            "java",
            str(ROOT / "src" / "test" / "java" / "project2"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["files"]
    assert payload["classes"]
    assert payload["relationships"]
    assert payload["diagnostics"] == []
