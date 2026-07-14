# Language-Agnostic UML and VS Code Workflow Design

## Goal

Make python2uml analyze Python, Java, C++, and C through real language parsers, convert every parser result into one normalized AST, run shared language-agnostic analyzers, and preview diagrams in VS Code before the user chooses whether and where to save them.

## Scope

This patch covers parser architecture, normalized models, UML heuristics, C conventions, diagnostics, fixtures, automated tests, dependency management, and VS Code commands, context menus, preview, and saving. It preserves Graphviz and draw.io rendering and remains heuristic rather than attempting semantic compilation or mixed-language analysis.

## Dependencies

Replace `requirements.txt` with `pyproject.toml`. Runtime dependencies are the Graphviz Python package, Tree-sitter Python bindings, and maintained C, C++, and Java grammar packages. Development dependencies include pytest and Black.

The extension requires Python, creates `.venv` with standard-library `venv` on first use, and installs the project with pip. Later runs reuse it. Black is configured with `line-length = 200` and runs on every modified Python file.

## Architecture

```text
selected paths
  -> ProjectLoader language filtering
  -> registered language parser
  -> normalized modules and source diagnostics
  -> shared class and relationship analyzers
  -> UML model
  -> temporary preview or saved renderer output
```

Python continues to use standard-library `ast`. Java, C++, and C use Tree-sitter and their maintained grammars. Each language has a separate explicit adapter. Manual regex source parsing is removed.

`AbstractSyntaxTreeLoader` becomes a small language-to-parser dispatcher. Adding a language requires a grammar dependency, one adapter, a `ProjectLanguage` entry, extension metadata, and file-extension metadata. Shared analyzers and renderers do not change.

## Normalized AST Boundary

Adapters emit normalized modules containing classes, structs, file classes, nesting, class kinds, modifiers, bases, abstract and pure-virtual facts, attributes, methods, parameters, returns, instantiations, member assignments, collection insertions, C include/macro/global facts, and source diagnostics.

Analyzers accept only normalized dataclasses. They never receive raw source, file handles, Python AST nodes, or Tree-sitter nodes. Tests enforce the boundary by constructing normalized input directly.

## Class Kinds

- Python `Protocol` becomes an interface; `ABC` or abstract methods make an abstract class.
- Java uses native `interface` and `abstract class` declarations.
- A C++ class is an interface when all public non-constructor behavior is pure virtual, it has no state or concrete behavior, and only a defaulted or pure-virtual destructor is additionally allowed.
- Other C++ classes with pure virtual methods are abstract; remaining classes are ordinary.
- C file/header objects and structs are ordinary classes.

## Relationship Evidence

Parsers report facts and analyzers infer relationships using deterministic evidence tiers:

- Composition: constructor-created member, C/C++ value member, or nested-class ownership.
- Aggregation: externally supplied member reference, pointer/reference member, or typed collection storing supplied objects.
- Association: parameter, return type, local use/instantiation, or C file include without retained ownership.

For a source-target pair, composition wins over aggregation, which wins over association. Inheritance and implementation remain separate structural relationships. A concrete type inheriting a normalized interface produces implementation; other project-local bases produce inheritance.

Both endpoints must be declared in the analyzed project. External type names remain visible in signatures but never create nodes or edges, including external bases.

## C Mapping

Every selected `.c` and `.h` file becomes a file class. Structs become inner classes owned by their declaring file class. Macros and global variables become file-class attributes. A function whose first parameter is a pointer to a known struct becomes a struct method; other functions remain file-class methods. Includes create associations only when the included file is analyzed.

Embedded struct values provide composition evidence, pointer/reference fields provide aggregation evidence, and function parameters/local uses provide association evidence.

## Diagnostics and Partial Results

Diagnostics contain path, line, column, severity, and parser message. Python `SyntaxError` and Tree-sitter error or missing nodes become source diagnostics, explicitly labeled so they are not confused with extension implementation errors.

Adapters retain valid declarations outside malformed regions. Preview continues when a usable UML model exists and fails only when nothing usable can be produced.

## VS Code Workflow

The Activity Bar and Command Palette expose Generate UML for Python, Java, C++, and C. These commands open language-filtered multi-file pickers.

Explorer file and folder context menus share a `Generate UML for...` submenu with the four languages. Multi-selection analyzes all compatible selected files and folders together. Paths are deduplicated; incompatible resources are skipped with a warning. Folders are recursively filtered by the Python loader.

Generation writes a temporary SVG and opens a webview showing the diagram, grouped source diagnostics, and a `Save As...` button. Saving SVG copies the preview. Other Graphviz formats and draw.io rerender the same inputs to the selected path. Closing the panel removes temporary files. The extension owns UI and process launching; Python owns parsing, analysis, diagnostics, and rendering.

## Fixtures and Manual Validation

Each of `src/test/python`, `src/test/java`, `src/test/cpp`, and `src/test/c` contains `project1` (small-to-medium) and `project2` (medium-to-large). The larger project exercises nesting, abstraction/interfaces, inheritance, implementation, association, aggregation, and composition where applicable.

`analyze_test_projects.py` accepts a language and paths and prints files, normalized/analyzed classes, relationships, and diagnostics as JSON.

## Automated Verification

Use comprehensive pytest coverage:

- Adapter tests assert normalized declarations, facts, and recovery.
- Analyzer tests use hand-built normalized nodes and cover evidence and precedence.
- Parametrized end-to-end tests analyze all eight projects and assert exact classes, kinds, members, relationships, and diagnostics.
- C tests cover file/header classes, structs, macros/globals, includes, ownership, and struct-pointer methods.
- CLI tests cover language selection, partial results, diagnostics, preview output, and saved formats while isolating external Graphviz availability.
- TypeScript tests cover pure selection, menu, and preview helpers where practical, followed by compilation and ESLint.

Expected values remain ordinary Python structures; no snapshot plugin is added.

## Documentation and Hygiene

`AGENTS.md` is updated before implementation and ignored as requested. README documents supported languages, first-run environment creation, parser limits, diagnostics, preview/save behavior, and manual validation. Generated diagrams, previews, virtual environments, caches, and compiled output remain ignored.

## Non-Goals

- Full semantic type resolution or compiler toolchain integration
- Mixed-language analysis
- Runtime ownership analysis
- External placeholder nodes or edges
- Generic Tree-sitter query/configuration framework
- Bundled cross-platform Python environments
- Relationship confidence scoring

