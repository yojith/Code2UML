# python2uml

Generate UML-style diagrams from Python, Java, C++, and C projects in VS Code or from the command line.

Python is parsed with the standard-library `ast` module. Java, C++, and C use the official Tree-sitter grammar packages `tree-sitter-java`, `tree-sitter-cpp`, and `tree-sitter-c`. All four adapters produce the same normalized model before shared analysis and rendering.

## Requirements

- Python 3.11 or newer with `pip`
- [Graphviz](https://graphviz.org/download/) with `dot` on `PATH` for preview and Graphviz formats

The VS Code extension creates a private `.venv` in extension storage and installs this project with pip the first time it runs. Later runs reuse that environment.

For CLI development, install the project and test tools from `pyproject.toml`:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

On macOS or Linux, use `.venv/bin/python` instead.

## VS Code workflow

Choose **Generate UML for Python**, **Java**, **C++**, or **C** from the Python2UML Activity Bar, Command Palette, or Explorer's **Generate UML for...** submenu. Activity Bar and Command Palette commands open a language-filtered picker that accepts multiple files and folders. Explorer multi-selection analyzes compatible resources together, recursively filters folders, deduplicates paths, and warns about skipped incompatible entries.

Generation opens a temporary SVG preview. The webview lists source diagnostics separately and offers **Save As...**. Saving SVG copies the preview; PNG, PDF, JPG, and draw.io selections rerender the same inputs. Closing the preview removes its temporary session files.

## CLI

Pass one language and one or more files or folders:

```bash
.venv/Scripts/python src/python/main.py --project-type java --output diagram.svg --paths src/test/java/project1
```

Project types are `python`, `java`, `cpp`, and `c`. The output extension selects a Graphviz format; `.drawio` selects draw.io XML. A successful run writes one JSON object to stdout containing `output`, `classes`, `relationships`, and `diagnostics`. Invalid input, an unusable model, or rendering failure writes an error to stderr and exits nonzero. Recoverable parser errors remain in `diagnostics` while valid declarations are rendered.

## Model behavior and limits

- Interfaces, abstract classes, inheritance, implementation, association, aggregation, composition, and nesting are inferred from normalized declarations and ownership evidence.
- C files and headers become file classes; structs are nested classes, macros/globals are attributes, and struct-pointer receiver functions become struct methods.
- A relationship is emitted only when both endpoints are declared in the analyzed project. External names remain visible in signatures but do not create placeholder nodes or edges.
- Analysis is heuristic, single-language, and source-based. It does not run a compiler, perform full semantic type resolution, infer runtime ownership, or analyze mixed-language projects.
- When evidence competes for one source-target pair, composition wins over aggregation, which wins over association.

## Fixtures and manual inspection

The eight projects under `src/test/{python,java,cpp,c}/{project1,project2}` exercise the supported language mappings. Inspect normalized/analyzed output and diagnostics as JSON with:

```bash
.venv/Scripts/python src/python/analyze_test_projects.py --language cpp --pretty src/test/cpp/project1 src/test/cpp/project2
```

Replace `cpp` and the paths with `python`, `java`, or `c` to inspect the other fixtures.

## Verification

```bash
.venv/Scripts/python -m black --check src/python tests
.venv/Scripts/python -m pytest -v
npm run compile
npm run lint
npm test
```

## License

MIT
