# python2uml

Generate UML-style diagrams from Python, Java, C++, and C projects in VS Code or from the command line.

Python is parsed with the standard-library `ast` module. Java, C++, and C use the official Tree-sitter grammar packages `tree-sitter-java`, `tree-sitter-cpp`, and `tree-sitter-c`. All four adapters produce the same normalized model before shared analysis and rendering.

## Requirements

The Marketplace extension requires a Windows x64 extension host. It bundles its own Python runtime and Graphviz, so no separate Python, virtual environment, pip installation, or Graphviz installation is needed.

WSL, remote extension hosts (including SSH and dev containers), Windows ARM64, Linux, and macOS are not supported.

Source CLI development requires Python 3.11 or newer. Graphviz-backed output also requires [Graphviz](https://graphviz.org/download/) with `dot.exe` on `PATH` and `EXTENSION_GRAPHVIZ_DOT` set to its absolute path; draw.io output does not. Install the project and test tools from `pyproject.toml`:

```powershell
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

On macOS or Linux, use `.venv/bin/python` instead.

## VS Code workflow

Choose **Generate UML for Python**, **Java**, **C++**, or **C** from the Python2UML Activity Bar, Command Palette, or Explorer's **Generate UML for...** submenu. Activity Bar and Command Palette commands open a language-filtered picker that accepts multiple files and folders. Explorer multi-selection analyzes compatible resources together, recursively filters folders, deduplicates paths, and warns about skipped incompatible entries.

Generation opens a temporary SVG preview. The webview lists source diagnostics separately and offers **Save As...**. Saving SVG copies the preview; PNG, PDF, JPG, and draw.io selections rerender the same inputs. Closing the preview removes its temporary session files.

Before testing the extension in an Extension Development Host on Windows x64, assemble the bundled runtime:

Runtime assembly requires [uv](https://docs.astral.sh/uv/) on `PATH` to install the locked build and production dependencies.

```powershell
npm run build:runtime:win32-x64
```

## CLI

The CLI is supported from a cloned source checkout. It is not separately distributed and Marketplace users do not need it. Before requesting SVG or another Graphviz-backed format, select the same absolute `dot.exe` exposed on `PATH`:

```powershell
$env:EXTENSION_GRAPHVIZ_DOT = (Get-Command dot.exe -ErrorAction Stop).Source
```

Then pass one language and one or more files or folders:

```powershell
& .\.venv\Scripts\python.exe -m python2uml --project-type java --output diagram.svg --paths tests\fixtures\java\project1
uvx --from . python2uml --project-type java --output diagram.svg --paths tests\fixtures\java\project1
uvx --from "C:\path\to\python2uml" python2uml --project-type java --output diagram.svg --paths "C:\path\to\sources"
```

uv is optional for ordinary source CLI invocation, required only when assembling the extension runtime, and not required by Marketplace users.

Project types are `python`, `java`, `cpp`, and `c`. The output extension selects a Graphviz format; `.drawio` selects draw.io XML. A successful run writes one JSON object to stdout containing `output`, `classes`, `relationships`, and `diagnostics`. Invalid input, an unusable model, or rendering failure writes an error to stderr and exits nonzero. Recoverable parser errors remain in `diagnostics` while valid declarations are rendered.

## Model behavior and limits

- Interfaces, abstract classes, inheritance, implementation, association, aggregation, composition, and nesting are inferred from normalized declarations and ownership evidence.
- C files and headers become file classes; structs are nested classes, macros/globals are attributes, and struct-pointer receiver functions become struct methods.
- A relationship is emitted only when both endpoints are declared in the analyzed project. External names remain visible in signatures but do not create placeholder nodes or edges.
- Analysis is heuristic, single-language, and source-based. It does not run a compiler, perform full semantic type resolution, infer runtime ownership, or analyze mixed-language projects.
- When evidence competes for one source-target pair, composition wins over aggregation, which wins over association.

## Fixtures and tests

The eight maintained fixtures live under `tests/fixtures/{python,java,cpp,c}/{project1,project2}`. Python tests live in `tests/python`; VS Code tests live in `tests/extension`.

## Verification

```powershell
& .\.venv\Scripts\python.exe -m black --check src\python2uml tests\python
& .\.venv\Scripts\python.exe -m pytest -v
npm run compile
npm run lint
npm test
```

## License

MIT
