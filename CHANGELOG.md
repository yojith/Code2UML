# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-07-28

### Added

- Generate UML for Python, Java, C++, and C projects.
- Preview diagrams in VS Code, with zoom controls, diagnostics, and clearer source-file reporting.
- Export structured, editable draw.io diagrams with Graphviz-powered layout, orthogonal routes, and better handling of connected and looping relationships.
- Run the tool from an installed package or directly from a source checkout.
- Bundle the Windows Python runtime with its release and licensing information; require Graphviz `dot.exe` on `PATH`.

### Changed

- Simplified the repository layout and split CI into separate build, test, and release workflows.
- Improved the packaged extension and added checks for its runtime, draw.io output, and VSIX contents.

### Fixed

- Fixed draw.io routes and zoom anchors, preview assets, renderer labels, and Windows runtime checks.

### Removed

- Removed obsolete examples and disposable files from the repository and packaged extension.

## [0.1.0] - 2026-06-24

- Established the core architecture for AST parsing, relationship analysis, and rendering
- Implemented the initial UML generation pipeline for Python projects
- Added basic heuristics for inheritance, association, aggregation, and composition
- Added VS Code commands for generating diagrams from Python files and folders
- Added Graphviz-based rendering with UML-style edge handling

[unreleased]: https://github.com/yojith/Code2UML/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/yojith/Code2UML/releases/tag/v0.1.1
[0.1.0]: https://github.com/yojith/Code2UML/releases/tag/v0.1.0
