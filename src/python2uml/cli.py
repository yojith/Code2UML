"""Command line entrypoint for the UML generator."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Sequence

from python2uml.generator import generate_uml_from_files
from python2uml.model.enums import ProjectLanguage


def _parse_project_language(value: str) -> ProjectLanguage:
    try:
        return ProjectLanguage(value.lower())
    except ValueError as exc:
        valid = ", ".join(language.value for language in ProjectLanguage)
        raise argparse.ArgumentTypeError(f"project type must be one of: {valid}") from exc


def parse_arguments(argv: Sequence[str] | None = None) -> tuple[ProjectLanguage, str, tuple[str, ...]]:
    parser = argparse.ArgumentParser(description="Generate UML diagrams from Python, Java, C++, and C source files")
    parser.add_argument(
        "-t",
        "--project-type",
        required=True,
        type=_parse_project_language,
        help="Project type to analyze; mixed-language input is not supported",
    )
    parser.add_argument("-o", "--output", default="uml_diagram", help="Output path or base filename (extension optional; use .drawio for draw.io output)")
    parser.add_argument("-p", "--paths", nargs="+", required=True, help="Source file or folder paths to analyze")
    args = parser.parse_args(argv)
    return args.project_type, args.output, tuple(args.paths)


def main(argv: Sequence[str] | None = None) -> int:
    project_type, output_file, file_paths = parse_arguments(argv)
    try:
        result = generate_uml_from_files(project_type, output_file, *file_paths)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "output": output_file,
                "classes": {name: asdict(uml_class) for name, uml_class in result.diagram.classes.items()},
                "relationships": [asdict(relationship) for relationship in result.diagram.relationships],
                "diagnostics": [asdict(diagnostic) for diagnostic in result.diagnostics],
                "documents": [str(Path(source_file).resolve()) for source_file in result.source_files],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
