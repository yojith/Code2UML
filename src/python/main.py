"""Command line entrypoint for the UML generator."""

from __future__ import annotations

import argparse

from generator import generate_uml_from_files


def parse_arguments() -> tuple[str, tuple[str, ...]]:
    parser = argparse.ArgumentParser(description="Generate UML diagrams from Python files")
    parser.add_argument("-o", "--output", default="uml_diagram", help="Output path or base filename (extension optional; default: uml_diagram)")
    parser.add_argument("-p", "--paths", nargs="+", required=True, help="Python file paths to analyze")
    args = parser.parse_args()
    return args.output, tuple(args.paths)


def main() -> None:
    output_file, file_paths = parse_arguments()
    generate_uml_from_files(output_file, *file_paths)


if __name__ == "__main__":
    main()
