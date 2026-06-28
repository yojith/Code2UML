"""Command line entrypoint for the UML generator."""

from __future__ import annotations

import argparse

from generator import generate_uml_from_files
from model.enums import ProjectLanguage


def _parse_project_language(value: str) -> ProjectLanguage:
    try:
        return ProjectLanguage(value.lower())
    except ValueError as exc:
        valid = ", ".join(language.value for language in ProjectLanguage)
        raise argparse.ArgumentTypeError(f"project type must be one of: {valid}") from exc


def parse_arguments() -> tuple[ProjectLanguage, str, tuple[str, ...]]:
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
    args = parser.parse_args()
    return args.project_type, args.output, tuple(args.paths)


def main() -> None:
    project_type, output_file, file_paths = parse_arguments()
    generate_uml_from_files(project_type, output_file, *file_paths)


if __name__ == "__main__":
    main()
