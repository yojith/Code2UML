"""Dump analyzer output for test projects in JSON."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from analyzers.class_analyzer import ClassAnalyzer
from analyzers.relationship_analyzer import RelationshipAnalyzer
from model.enums import ProjectLanguage
from parser.abstracter import AbstractSyntaxTreeLoader
from parser.project_loader import ProjectLoader


def parse_arguments() -> tuple[ProjectLanguage, list[str], bool]:
    parser = argparse.ArgumentParser(description="Analyze test projects and print JSON output")
    parser.add_argument("--language", required=True, choices=[language.value for language in ProjectLanguage])
    parser.add_argument(
        "paths",
        nargs="*",
        default=[str(Path(__file__).resolve().parents[1] / "test")],
        help="Files or folders to analyze (default: src/test)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON output")
    args = parser.parse_args()
    return ProjectLanguage(args.language), list(args.paths), bool(args.pretty)


def main() -> None:
    language, paths, pretty = parse_arguments()
    loader = ProjectLoader()
    ast_loader = AbstractSyntaxTreeLoader()
    class_analyzer = ClassAnalyzer()
    relationship_analyzer = RelationshipAnalyzer()

    filepaths = loader.collect_source_files(language, *paths)
    modules = ast_loader.load(language, *filepaths)
    diagram = class_analyzer.analyze(modules)
    relationship_analyzer.analyze(modules, diagram)

    payload = {
        "paths": paths,
        "files": filepaths,
        "classes": {name: asdict(uml_class) for name, uml_class in diagram.classes.items()},
        "relationships": [asdict(relationship) for relationship in diagram.relationships],
        "diagnostics": [asdict(diagnostic) for module in modules for diagnostic in module.diagnostics],
    }
    print(json.dumps(payload, indent=2 if pretty else None, sort_keys=True))


if __name__ == "__main__":
    main()
