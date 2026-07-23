# Bundled Windows Runtime Design

## Goal

Package Python2UML as a self-contained Windows x64 VS Code extension. A user installs the platform-specific VSIX and can generate diagrams without installing Python, Python packages, Graphviz, or `dot.exe`, and without network access or first-run setup.

The initial release supports only a `win32-x64` extension host. WSL, Remote SSH, dev containers, Codespaces, Windows ARM64, Linux, and macOS are out of scope and must receive a clear unsupported-platform error.

## Current Rendering Path

The current extension does not run a persistent backend. Each generation follows this path:

```text
generateUML()
-> setupVenv()
-> runScript()
-> python -m python2uml
-> GraphvizRenderer.render()
-> graphviz.Digraph.render()
-> dot discovered on PATH
-> Python exits
```

`GraphvizRenderer._ensure_dot_available()` calls `shutil.which("dot")`. The installed Python `graphviz` package separately invokes the native `dot` program when `Digraph.render()` runs. Draw.io output bypasses Graphviz, while preview and Graphviz-backed output formats require it.

The migration preserves the one-shot CLI and `Digraph.render()` behavior. It replaces user-side environment setup and system executable discovery; it does not introduce a persistent process, custom backend protocol, or replacement DOT renderer.

## Packaged Layout

The generated Windows x64 extension contains:

```text
extension/
|-- out/src/extension.js
|-- python-runtime/
|   |-- python.exe
|   |-- python312._pth
|   |-- python312.zip
|   `-- Lib/site-packages/
|       |-- python2uml/
|       `-- production dependencies
|-- graphviz/
|   |-- bin/dot.exe
|   |-- lib/
|   |-- share/
|   `-- remaining files from the official archive
|-- licenses/
|   |-- python/
|   `-- graphviz/
|-- THIRD_PARTY_NOTICES.md
`-- package.json
```

The implementation retains the repository's existing `out/src/extension.js` entry point. It does not add a second JavaScript bundling layout.

`python-runtime/` and `graphviz/` are generated locally or in CI and ignored by Git. `.vscodeignore` must include both generated trees, the license trees, notices, compiled extension output, and required package metadata in the VSIX while continuing to exclude source, tests, caches, local virtual environments, and unrelated artifacts.

## Pinned Runtime Inputs

The first runtime uses:

- CPython 3.12.10 Windows embeddable package, 64-bit, downloaded from the official Python release archive.
- Graphviz 15.0.0 `windows_10_cmake_Release_Graphviz-15.0.0-win64.zip`, downloaded from the official Graphviz GitLab release.

The PowerShell build script stores the exact URLs and expected SHA-256 digests as constants. It downloads archives into a temporary directory, verifies each digest before extraction, and fails closed on mismatch. It never selects a newer version automatically.

Python 3.12.10 is compatible with the project's `requires-python = ">=3.11"`. The embeddable distribution is configured by adding `Lib/site-packages` and enabling `import site` in `python312._pth`.

The repository will commit `uv.lock`. Runtime dependencies are resolved from that lock, and a build-time CPython 3.12 x64 installation installs the root package plus production dependencies into `python-runtime/Lib/site-packages`. Development dependencies, pip, build caches, bytecode caches, tests, and source-control files are not copied into the finished runtime.

## Runtime Assembly

One repository-owned PowerShell script assembles and verifies the runtime. Both local development and Windows GitHub Actions invoke this script; the workflow does not duplicate its download, extraction, installation, or smoke-test commands.

The script:

1. Refuses to run on a non-Windows or non-x64 host.
2. Removes only its known generated `python-runtime/` and `graphviz/` directories after resolving and verifying that they are direct children of the repository root.
3. Downloads the pinned Python and Graphviz ZIP archives to a temporary directory.
4. Verifies their committed SHA-256 values.
5. Extracts CPython into `python-runtime/` and configures `python312._pth`.
6. Uses the build-time Python tooling and the committed lock to install the backend and production dependencies into `python-runtime/Lib/site-packages`.
7. Extracts the complete official Graphviz runtime root into `graphviz/` without maintaining a handwritten file allowlist.
8. Copies authoritative Python and Graphviz redistribution licenses into their packaged license directories.
9. Removes package caches and `__pycache__` directories from generated output.
10. Verifies bundled Python imports `python2uml`, bundled `dot.exe` starts, and the real backend renders SVG through bundled Graphviz.

The complete Graphviz archive layout is retained for the first release. Runtime-size pruning is deferred until required formats are documented and automated tests prove specific files unnecessary.

## Extension Runtime Behavior

`setupVenv()` and its project marker are removed. The extension instead resolves these absolute paths from `ExtensionContext.extensionUri`:

```text
python-runtime/python.exe
graphviz/bin/dot.exe
```

Before invoking the backend, it verifies:

- `process.platform === "win32"`;
- `process.arch === "x64"`;
- bundled Python is a file;
- bundled `dot.exe` is a file.

The existing one-shot `execFile` invocation remains. Each invocation receives a new environment object copied from `process.env`, with these child-only changes:

```text
EXTENSION_GRAPHVIZ_DOT=<absolute bundled graphviz/bin/dot.exe>
PYTHONNOUSERSITE=1
PYTHONUNBUFFERED=1
PATH=<absolute bundled graphviz/bin>;<inherited PATH>
```

This object affects only bundled Python and its descendants. It does not mutate VS Code's `process.env` or persistent user/system environment variables.

Prepending the bundled Graphviz directory is required because the installed Python `graphviz` library launches `dot` by command name and exposes no suitable per-render public executable-path argument. The dedicated environment variable makes the selected binary explicit and lets Python reject missing or inconsistent configuration. No production fallback to system Python or system Graphviz is permitted.

Local Extension Development Host runs use the same generated runtime paths. There is no developer interpreter override; developers run the PowerShell assembly script before exercising generation commands.

## Python Graphviz Validation

The renderer replaces `shutil.which("dot")` with one small resolver for `EXTENSION_GRAPHVIZ_DOT`. It requires an absolute path to an existing file and verifies that the first `dot.exe` resolved from the child `PATH` is the same file. This ensures `Digraph.render()` invokes the exact bundled executable while preserving all existing graph construction and output behavior.

Missing, relative, nonexistent, or mismatched paths raise a direct runtime error naming the configured path. Draw.io generation continues to bypass Graphviz, but the extension still validates the complete bundled runtime before invoking any packaged backend command because a valid installation must be internally consistent.

## Error Reporting

Unsupported hosts fail before process launch with a message stating the detected platform and architecture and that the current package supports only Windows x64.

Missing runtime components report their resolved absolute paths. Backend failures retain the current single-error flow and add available process exit code, stderr, executable path, requested output format, platform, and architecture. Errors do not trigger downloads, repairs, system searches, venv creation, or pip execution.

## CI and Release Packaging

The existing cross-platform test workflow remains responsible for ordinary Python tests. Windows x64 build and release jobs run on `windows-latest` and perform:

1. Checkout.
2. Node setup and `npm ci`.
3. Build-time CPython 3.12 x64 and `uv` setup.
4. Existing Python tests, TypeScript compile, ESLint, and VS Code tests.
5. The PowerShell runtime assembly script.
6. Runtime smoke tests performed by that script.
7. `vsce package --target win32-x64`.
8. VSIX ZIP inspection for compiled JavaScript, bundled `python.exe`, backend package metadata, production dependencies, `dot.exe`, Graphviz `lib/` and `share/`, licenses, and notices.
9. Negative inspection for local venvs, tests, caches, source-control metadata, development dependencies, and unrelated platform runtimes.
10. Artifact upload or Marketplace publication.

The backend smoke test uses bundled Python to run the real CLI against a committed minimal source fixture with `EXTENSION_GRAPHVIZ_DOT` and the child `PATH` configured exactly as the extension configures them. It asserts a successful exit and an SVG containing an `<svg` element. A separate test-only Graphviz adapter and pytest inside the packaged runtime are unnecessary.

## Tests

TypeScript tests replace venv-creation assertions with focused checks that:

- bundled paths resolve from the extension URI, including paths containing spaces;
- only `win32-x64` is accepted;
- missing runtime components fail before launch;
- `runScript()` receives the bundled executable and the child-only environment;
- bundled Graphviz `bin` is first on the child `PATH`;
- the parent environment object is not mutated;
- stdout payload parsing and failure reporting remain intact.

Python tests cover the Graphviz resolver's missing, relative, nonexistent, mismatched, and valid bundled paths, then reuse the existing renderer tests to confirm UML rendering semantics remain unchanged.

CI provides the real binary integration coverage: `python-runtime/python.exe` imports the backend, `graphviz/bin/dot.exe -V` succeeds, SVG is supported, and the real CLI produces SVG using only packaged components.

Before completion, run the repository-required Black check, full pytest suite, TypeScript compile, ESLint, VS Code tests, `git diff --check`, and parser-regex search.

## Licensing

`THIRD_PARTY_NOTICES.md` records the pinned Python and Graphviz versions, upstream project and release URLs, licenses, whether packaged files were modified, and where authoritative license texts are included. The build copies upstream license files rather than paraphrasing them. Redistribution notices must be reviewed before Marketplace publication.

## Deferred Work

The first release deliberately excludes persistent backend processes, developer interpreter overrides, system-runtime fallback, runtime repair, automatic user-side downloads, PyInstaller/Nuitka, Graphviz pruning, Windows ARM64, Linux, macOS, WSL, Remote SSH, dev containers, and Codespaces.

Platform support is added later through separate platform-specific VSIX packages, never by placing every runtime in one universal package.

## Definition of Done

The migration is complete when:

- generated Python and Graphviz runtimes are absent from Git and present in the Windows x64 VSIX;
- pinned downloads are checksum-verified;
- backend and locked production dependencies are preinstalled;
- Python and Graphviz redistribution notices are packaged;
- the extension launches only bundled Python;
- the backend invokes only bundled Graphviz;
- no normal-user venv, pip, download, system PATH discovery, or network access occurs;
- unsupported extension hosts fail clearly;
- CI smoke-tests the exact packaged runtime and inspects the VSIX contents;
- the installed Windows x64 extension generates SVG without system Python or Graphviz.
