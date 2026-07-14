# Language-Agnostic UML and VS Code Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse Python, Java, C++, and C into one normalized AST, infer UML relationships with shared analyzers, and preview diagrams in VS Code before saving.

**Architecture:** Python uses `ast`; Java, C++, and C use dedicated Tree-sitter adapters. Every adapter emits normalized dataclasses and diagnostics, and analyzers consume only that normalized model. The VS Code extension selects language-scoped inputs, invokes the Python CLI, displays its temporary SVG and diagnostics in a webview, and saves only on request.

**Tech Stack:** Python 3.11+, `ast`, `tree-sitter`, `tree-sitter-java`, `tree-sitter-cpp`, `tree-sitter-c`, pytest, Black, Graphviz, TypeScript, VS Code Extension API.

## Global Constraints

- Do not discard or reset existing uncommitted user changes.
- Do not use regex to parse source-language structure.
- Analyzers may consume only normalized dataclasses; they may not read source or inspect parser-native nodes.
- External type names remain in signatures but never become UML nodes or edges.
- Relationship precedence is composition > aggregation > association.
- Python uses standard-library `ast`; Java, C++, and C use Tree-sitter.
- Modified Python files must be formatted with Black using `line-length = 200`.
- The extension creates `.venv` with `venv` and installs runtime dependencies with pip on first use.
- Keep `AGENTS.md` ignored and update it before and after implementation milestones.

---

## Planned File Structure

- `pyproject.toml`: project metadata, runtime/dev dependencies, pytest configuration, and Black line length.
- `src/python/parser/normalized_ast.py`: parser-independent declarations, evidence facts, and diagnostics.
- `src/python/parser/abstracter.py`: small parser registry/dispatcher only.
- `src/python/parser/python_parser.py`: Python `ast` to normalized AST.
- `src/python/parser/tree_sitter_helpers.py`: shared Tree-sitter node text, traversal, type text, and diagnostic helpers used by three adapters.
- `src/python/parser/java_parser.py`: Java Tree-sitter adapter.
- `src/python/parser/cpp_parser.py`: C++ Tree-sitter adapter.
- `src/python/parser/c_parser.py`: C Tree-sitter adapter and C file-class conventions.
- `src/python/analyzers/class_analyzer.py`: normalized declarations to UML classes.
- `src/python/analyzers/relationship_analyzer.py`: normalized evidence to ranked project-local UML edges.
- `src/python/generator.py`: analysis/render orchestration returning diagnostics.
- `src/python/main.py`: CLI and JSON status output.
- `src/python/analyze_test_projects.py`: language-aware manual JSON inspection.
- `tests/`: focused parser, analyzer, generator/CLI, loader, and end-to-end pytest tests.
- `src/test/{python,java,cpp,c}/project{1,2}`: real fixture projects.
- `src/languages.ts`: one source of truth for language labels/extensions/command IDs.
- `src/filePicker.ts`: language-filtered file and save dialogs.
- `src/pythonRunner.ts`: first-run `.venv` creation, pip installation, and CLI invocation.
- `src/umlGenerator.ts`: input resolution, generation session, and rerender/save coordination.
- `src/previewPanel.ts`: safe webview preview, diagnostics, Save As messaging, and cleanup.
- `src/extension.ts`: command registration and Activity Bar items.
- `package.json`: command, view, submenu, and Explorer context contributions.

### Task 1: Dependency Metadata and Normalized Contracts

**Files:**
- Create: `pyproject.toml`
- Delete: `requirements.txt`
- Modify: `src/python/parser/normalized_ast.py:1-55`
- Create: `tests/conftest.py`
- Create: `tests/test_normalized_ast.py`

**Interfaces:**
- Produces: `SourceDiagnostic`, `NormalizedTypeReference`, `NormalizedMemberAssignment`, `NormalizedClass`, `NormalizedModule`.
- `NormalizedModule.diagnostics` is `list[SourceDiagnostic]`.
- `NormalizedClass.member_assignments` describes constructed versus supplied member values without source access.

- [ ] **Step 1: Write failing normalized-contract tests**

```python
from parser.normalized_ast import NormalizedClass, NormalizedMemberAssignment, NormalizedModule, SourceDiagnostic


def test_normalized_module_carries_diagnostics_and_evidence():
    module = NormalizedModule(
        path="broken.java",
        classes=[NormalizedClass(name="Order", member_assignments=[NormalizedMemberAssignment("customer", "Customer", "supplied")])],
        diagnostics=[SourceDiagnostic("broken.java", 4, 9, "error", "unexpected token")],
    )
    assert module.classes[0].member_assignments[0].ownership == "supplied"
    assert module.diagnostics[0].line == 4
```

- [ ] **Step 2: Run the test and verify the old model fails**

Run: `python -m pytest tests/test_normalized_ast.py -v`

Expected: FAIL because `NormalizedMemberAssignment`, `SourceDiagnostic`, and the new fields do not exist.

- [ ] **Step 3: Add project metadata and the minimal normalized contracts**

Use these dependency/config sections in `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "python2uml"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "graphviz>=0.20,<1",
  "tree-sitter>=0.25,<0.27",
  "tree-sitter-c>=0.24,<0.25",
  "tree-sitter-cpp>=0.23,<0.24",
  "tree-sitter-java>=0.23,<0.24",
]

[project.optional-dependencies]
dev = ["black>=25,<27", "pytest>=8,<10"]

[tool.black]
line-length = 200

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src/python"]

[tool.setuptools]
py-modules = []
```

Add literal ownership values `constructed`, `supplied`, `value`, and `reference` to `NormalizedMemberAssignment`. Add `is_abstract`, `is_pure_virtual`, `is_static`, `parent`, `bases`, `type_references`, and diagnostics only where downstream tasks require them; do not add a generic metadata dictionary.

- [ ] **Step 4: Install and verify the contract**

Run: `python -m pip install -e ".[dev]"`

Run: `python -m pytest tests/test_normalized_ast.py -v`

Expected: PASS.

- [ ] **Step 5: Format and commit**

Run: `python -m black src/python/parser/normalized_ast.py tests/conftest.py tests/test_normalized_ast.py`

```bash
git add pyproject.toml requirements.txt src/python/parser/normalized_ast.py tests/conftest.py tests/test_normalized_ast.py
git commit -m "build: define normalized parser contracts"
```

### Task 2: Deterministic Normalized-Only Analyzers

**Files:**
- Modify: `src/python/analyzers/class_analyzer.py:1-44`
- Modify: `src/python/analyzers/relationship_analyzer.py:1-153`
- Modify: `src/python/model/enums.py:1-25`
- Modify: `src/python/model/uml_class.py:1-20`
- Create: `tests/test_analyzers.py`

**Interfaces:**
- Consumes: normalized contracts from Task 1.
- Produces: `ClassAnalyzer.analyze(modules: list[NormalizedModule]) -> UMLDiagram` and `RelationshipAnalyzer.analyze(modules: list[NormalizedModule], diagram: UMLDiagram) -> UMLDiagram`.

- [ ] **Step 1: Write analyzer tests with hand-built normalized nodes**

Cover class kinds, nested-class composition, external type suppression, implementation, and evidence ranking. The core precedence assertion must be:

```python
def test_strongest_relationship_evidence_wins():
    modules = [module_with_classes("Order", "Customer", evidence=("association", "aggregation", "composition"))]
    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)
    assert relationships(diagram, "Order", "Customer") == {RelationshipType.COMPOSITION}


def test_external_types_stay_in_signatures_without_edges():
    modules = [module_with_external_base_and_parameter("Controller", "FrameworkBase", "Request")]
    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)
    assert set(diagram.classes) == {"Controller"}
    assert diagram.relationships == []
    assert "request: Request" in diagram.classes["Controller"].methods[0].parameters
```

- [ ] **Step 2: Run tests and verify behavior gaps**

Run: `python -m pytest tests/test_analyzers.py -v`

Expected: FAIL on the new normalized facts and abstract/interface cases.

- [ ] **Step 3: Implement evidence-to-edge rules only in `RelationshipAnalyzer`**

Use one rank mapping:

```python
RELATIONSHIP_RANK = {
    RelationshipType.ASSOCIATION: 1,
    RelationshipType.AGGREGATION: 2,
    RelationshipType.COMPOSITION: 3,
}
```

Filter every candidate against `set(diagram.classes)` before adding it. Do not add confidence scores or parser-specific branches. Preserve inheritance and implementation separately from ownership ranking.

- [ ] **Step 4: Run analyzer tests**

Run: `python -m pytest tests/test_analyzers.py -v`

Expected: PASS.

- [ ] **Step 5: Format and commit**

Run: `python -m black src/python/analyzers src/python/model tests/test_analyzers.py`

```bash
git add src/python/analyzers src/python/model tests/test_analyzers.py
git commit -m "feat: infer relationships from normalized evidence"
```

### Task 3: Python AST Adapter and Parser Dispatcher

**Files:**
- Replace: `src/python/parser/abstracter.py:1-697`
- Create: `src/python/parser/python_parser.py`
- Create: `tests/parser/test_python_parser.py`
- Modify: `src/python/utils/ast_utils.py:1-25`

**Interfaces:**
- Produces: `PythonParser.parse(*paths: str) -> list[NormalizedModule]`.
- Produces: `AbstractSyntaxTreeLoader.load(language: ProjectLanguage, *paths: str) -> list[NormalizedModule]`; retain the current Python-only compatibility overload only if an existing caller still uses it.

- [ ] **Step 1: Write Python adapter tests**

Test `Protocol`, `ABC`, abstract methods, inner classes, constructor-created members, supplied members, collection insertion, async methods, forward-reference annotations, and partial diagnostics from a malformed file.

```python
def test_python_parser_normalizes_abstraction_and_ownership(tmp_path):
    source = write_python_fixture(tmp_path)
    module = PythonParser().parse(str(source))[0]
    assert class_by_name(module, "Repository").kind is ClassKind.INTERFACE
    assert assignment(class_by_name(module, "Service"), "repository").ownership == "supplied"
    assert assignment(class_by_name(module, "Service"), "cache").ownership == "constructed"
```

- [ ] **Step 2: Run and verify the adapter module is missing**

Run: `python -m pytest tests/parser/test_python_parser.py -v`

Expected: FAIL importing `parser.python_parser`.

- [ ] **Step 3: Move existing Python AST walking into `PythonParser` and shrink the dispatcher**

The dispatcher must contain only parser registration and selection:

```python
PARSERS = {ProjectLanguage.PYTHON: PythonParser}


class AbstractSyntaxTreeLoader:
    def load(self, language: ProjectLanguage, *paths: str) -> list[NormalizedModule]:
        return PARSERS[language]().parse(*paths)
```

Do not retain Java/C++/C regex helpers in this file.
Tasks 4-6 add their adapters to `PARSERS` as each module becomes available, so every intermediate commit remains runnable.

- [ ] **Step 4: Run Python parser and analyzer regression tests**

Run: `python -m pytest tests/parser/test_python_parser.py tests/test_analyzers.py -v`

Expected: PASS.

- [ ] **Step 5: Format and commit**

Run: `python -m black src/python/parser/abstracter.py src/python/parser/python_parser.py src/python/utils/ast_utils.py tests/parser/test_python_parser.py`

```bash
git add src/python/parser/abstracter.py src/python/parser/python_parser.py src/python/utils/ast_utils.py tests/parser/test_python_parser.py
git commit -m "refactor: isolate Python AST adapter"
```

### Task 4: Java Tree-sitter Adapter

**Files:**
- Create: `src/python/parser/tree_sitter_helpers.py`
- Create: `src/python/parser/java_parser.py`
- Create: `tests/parser/test_java_parser.py`
- Modify: `src/python/parser/abstracter.py:1-40`

**Interfaces:**
- Produces: `JavaParser.parse(*paths: str) -> list[NormalizedModule]`.
- Shared helper: `parse_tree(path: str, language_capsule: object) -> tuple[bytes, Node]` and `tree_diagnostics(path: str, root: Node) -> list[SourceDiagnostic]`.

- [ ] **Step 1: Write Java grammar tests using real source**

Cover packages, annotations, generics, nested classes, interfaces, abstract classes, `extends`, `implements`, fields, constructors, new expressions, supplied-field assignment, collections, and a recoverable syntax error.

```python
def test_java_parser_handles_generics_and_interface_implementation(java_project):
    modules = JavaParser().parse(*java_project)
    repository = find_class(modules, "Repository")
    service = find_class(modules, "OrderService")
    assert repository.kind is ClassKind.INTERFACE
    assert service.bases == ["Repository"]
    assert any(parameter.type_name == "List<Order>" for method in service.methods for parameter in method.parameters)
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/parser/test_java_parser.py -v`

Expected: FAIL because the Java adapter does not exist.

- [ ] **Step 3: Traverse named Tree-sitter fields and emit normalized facts**

Initialize the parser with the grammar capsule:

```python
from tree_sitter import Language, Parser
import tree_sitter_java

JAVA_LANGUAGE = Language(tree_sitter_java.language())
```

Use node types and `child_by_field_name`; use source slicing only to recover identifier/type spelling. Never apply regex to source text.

- [ ] **Step 4: Run Java adapter and analyzer tests**

Run: `python -m pytest tests/parser/test_java_parser.py tests/test_analyzers.py -v`

Expected: PASS.

- [ ] **Step 5: Format and commit**

Run: `python -m black src/python/parser/tree_sitter_helpers.py src/python/parser/java_parser.py src/python/parser/abstracter.py tests/parser/test_java_parser.py`

```bash
git add src/python/parser/tree_sitter_helpers.py src/python/parser/java_parser.py src/python/parser/abstracter.py tests/parser/test_java_parser.py
git commit -m "feat: parse Java with Tree-sitter"
```

### Task 5: C++ Tree-sitter Adapter

**Files:**
- Create: `src/python/parser/cpp_parser.py`
- Create: `tests/parser/test_cpp_parser.py`
- Modify: `src/python/parser/tree_sitter_helpers.py`
- Modify: `src/python/parser/abstracter.py:1-40`

**Interfaces:**
- Produces: `CppParser.parse(*paths: str) -> list[NormalizedModule]`.

- [ ] **Step 1: Write C++ grammar and class-kind tests**

Cover namespaces, templates, nested classes, multiple inheritance, visibility sections, constructors, initializer lists, out-of-class definitions, value/reference/pointer fields, local construction, pure virtual methods, and defaulted/pure destructors.

```python
def test_cpp_interface_heuristic(cpp_project):
    modules = CppParser().parse(*cpp_project)
    assert find_class(modules, "Repository").kind is ClassKind.INTERFACE
    assert find_class(modules, "BaseService").kind is ClassKind.ABSTRACT
    assert assignment(find_class(modules, "Order"), "address").ownership == "value"
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/parser/test_cpp_parser.py -v`

Expected: FAIL importing `parser.cpp_parser`.

- [ ] **Step 3: Implement explicit C++ Tree-sitter traversal**

Initialize with `Language(tree_sitter_cpp.language())`. Determine interface versus abstract from normalized method visibility/pure-virtual facts and normalized fields; do not inspect source in analyzers. Normalize qualified names to the project-local declared class name while retaining full type spelling in signatures.

- [ ] **Step 4: Run C++ and analyzer tests**

Run: `python -m pytest tests/parser/test_cpp_parser.py tests/test_analyzers.py -v`

Expected: PASS.

- [ ] **Step 5: Format and commit**

Run: `python -m black src/python/parser/cpp_parser.py src/python/parser/tree_sitter_helpers.py src/python/parser/abstracter.py tests/parser/test_cpp_parser.py`

```bash
git add src/python/parser/cpp_parser.py src/python/parser/tree_sitter_helpers.py src/python/parser/abstracter.py tests/parser/test_cpp_parser.py
git commit -m "feat: parse C++ with Tree-sitter"
```

### Task 6: C Tree-sitter Adapter and File-Class Model

**Files:**
- Create: `src/python/parser/c_parser.py`
- Create: `tests/parser/test_c_parser.py`
- Modify: `src/python/parser/tree_sitter_helpers.py`
- Modify: `src/python/parser/abstracter.py:1-40`

**Interfaces:**
- Produces: `CParser.parse(*paths: str) -> list[NormalizedModule]`.
- File class names are stable, path-derived, and collision-safe within an analysis run.

- [ ] **Step 1: Write C mapping tests**

Cover `.h` and `.c` file classes, includes, object-like and function-like macros, globals, typedef structs, anonymous structs, nested struct ownership, embedded versus pointer fields, struct-pointer first-parameter methods, and free functions.

```python
def test_c_parser_models_files_structs_and_function_ownership(c_project):
    modules = CParser().parse(*c_project)
    header = find_file_class(modules, "shop.h")
    cart = find_class(modules, "Cart")
    assert cart.parent == header.name
    assert "MAX_ITEMS" in {attribute.name for attribute in header.attributes}
    assert "cart_add" in {method.name for method in cart.methods}
    assert assignment(cart, "owner").ownership == "reference"
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/parser/test_c_parser.py -v`

Expected: FAIL importing `parser.c_parser`.

- [ ] **Step 3: Implement C Tree-sitter traversal and file conventions**

Initialize with `Language(tree_sitter_c.language())`. Resolve includes only against selected modules. Treat embedded struct fields as `value`, pointer fields as `reference`, and the first pointer-to-struct parameter as method ownership. Use syntax nodes, never source regex.

- [ ] **Step 4: Run C and analyzer tests**

Run: `python -m pytest tests/parser/test_c_parser.py tests/test_analyzers.py -v`

Expected: PASS.

- [ ] **Step 5: Format and commit**

Run: `python -m black src/python/parser/c_parser.py src/python/parser/tree_sitter_helpers.py src/python/parser/abstracter.py tests/parser/test_c_parser.py`

```bash
git add src/python/parser/c_parser.py src/python/parser/tree_sitter_helpers.py src/python/parser/abstracter.py tests/parser/test_c_parser.py
git commit -m "feat: model C projects with Tree-sitter"
```

### Task 7: Real Fixtures, Manual Inspector, and End-to-End Pytests

**Files:**
- Modify/Create: `src/test/python/project1/*`, `src/test/python/project2/*`
- Modify/Create: `src/test/java/project1/*`, `src/test/java/project2/*`
- Modify/Create: `src/test/cpp/project1/*`, `src/test/cpp/project2/*`
- Modify/Create: `src/test/c/project1/*`, `src/test/c/project2/*`
- Modify: `src/python/analyze_test_projects.py:1-55`
- Create: `tests/test_fixture_projects.py`
- Replace: `tests/test_project_loader_and_graphviz.py`
- Create: `tests/test_project_loader.py`
- Create: `tests/test_renderers.py`

**Interfaces:**
- `analyze_test_projects.py --language {python,java,cpp,c} [paths...] --pretty` prints files, classes, relationships, and diagnostics JSON.

- [ ] **Step 1: Define exact expected outcomes for all eight fixture projects**

Use a parametrized table with exact class names/kinds and relationship triples:

```python
@pytest.mark.parametrize("language,project,expected", CASES)
def test_fixture_project(language, project, expected):
    modules = load_fixture(language, project)
    diagram = analyze(modules)
    assert summarize_classes(diagram) == expected["classes"]
    assert summarize_relationships(diagram) == expected["relationships"]
    assert summarize_diagnostics(modules) == expected["diagnostics"]
```

Every `project2` must assert interface/abstract behavior, nesting, inheritance/implementation, association, aggregation, and composition where applicable.

- [ ] **Step 2: Run end-to-end tests against current fixtures**

Run: `python -m pytest tests/test_fixture_projects.py -v`

Expected: FAIL until fixtures and adapters agree on the approved model.

- [ ] **Step 3: Complete fixtures and make the manual inspector language-aware**

Add `--language` using `ProjectLanguage(value)` and include diagnostics in the JSON payload. Keep fixtures readable; do not generate large synthetic files.

- [ ] **Step 4: Run all Python tests and manual samples**

Run: `python -m pytest -v`

Run once per language: `python src/python/analyze_test_projects.py --language java --pretty src/test/java/project2`

Expected: pytest PASS; inspector prints valid JSON containing non-empty classes and relationships with no parser implementation exceptions.

- [ ] **Step 5: Format and commit**

Run: `python -m black src/python/analyze_test_projects.py tests`

```bash
git add src/test src/python/analyze_test_projects.py tests
git commit -m "test: validate all language fixture projects"
```

### Task 8: Generator Results, CLI Diagnostics, and Partial Analysis

**Files:**
- Modify: `src/python/generator.py:1-43`
- Modify: `src/python/main.py:1-42`
- Create: `tests/test_generator_cli.py`

**Interfaces:**
- Produces: `AnalysisResult(diagram: UMLDiagram, diagnostics: list[SourceDiagnostic])`.
- Produces: `UMLGenerator.analyze(project_type: ProjectLanguage, *paths: str) -> AnalysisResult`.
- `generate(...) -> AnalysisResult` renders then returns the same result.
- `main(argv: Sequence[str] | None = None) -> int` supports direct execution and test injection.
- CLI stdout is one JSON object containing `output`, `classes`, `relationships`, and `diagnostics`.

- [ ] **Step 1: Write partial-result and JSON protocol tests**

```python
def test_cli_renders_valid_declarations_and_reports_source_errors(tmp_path, capsys):
    source = write_partially_invalid_source(tmp_path)
    exit_code = main(["-t", "java", "-o", str(tmp_path / "preview.svg"), "-p", str(source)])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["classes"]
    assert payload["diagnostics"][0]["path"] == str(source)
```

- [ ] **Step 2: Run and verify the CLI lacks structured results**

Run: `python -m pytest tests/test_generator_cli.py -v`

Expected: FAIL because `AnalysisResult` and JSON output do not exist.

- [ ] **Step 3: Separate analyze from render and emit JSON once**

Raise a clear analysis error only when `diagram.classes` is empty. Send implementation failures to stderr/nonzero exit; keep analyzed-source diagnostics in the JSON result.

- [ ] **Step 4: Run generator, CLI, and fixture tests**

Run: `python -m pytest tests/test_generator_cli.py tests/test_fixture_projects.py -v`

Expected: PASS.

- [ ] **Step 5: Format and commit**

Run: `python -m black src/python/generator.py src/python/main.py tests/test_generator_cli.py`

```bash
git add src/python/generator.py src/python/main.py tests/test_generator_cli.py
git commit -m "feat: return partial UML results with diagnostics"
```

### Task 9: Data-Driven VS Code Commands and Multi-Selection Context Menus

**Files:**
- Create: `src/languages.ts`
- Modify: `src/filePicker.ts:1-63`
- Modify: `src/extension.ts:1-80`
- Modify: `src/umlGenerator.ts:1-90`
- Modify: `package.json:1-70`
- Modify: `src/test/extension.test.ts:1-30`

**Interfaces:**
- Produces: `LanguageId = "python" | "java" | "cpp" | "c"`.
- Produces: `LANGUAGES` entries containing label, extensions, and command ID.
- Command handlers accept `(clicked?: vscode.Uri, selected?: vscode.Uri[])`.
- Produces: `resolveSelectedPaths(language, clicked, selected) -> { paths: string[]; skipped: string[] }` as a pure testable helper.

- [ ] **Step 1: Write TypeScript tests for language filters and selected resources**

Test a multi-selection containing files, folders, duplicates, and an incompatible file. Assert that folders remain eligible for recursive Python filtering and incompatible files are reported in `skipped`.

- [ ] **Step 2: Compile tests and verify missing metadata/helper failures**

Run: `npm run compile`

Expected: FAIL until `languages.ts` and the new exports exist.

- [ ] **Step 3: Add one metadata table and register all commands from it**

Use the same table for Activity Bar items, file filters, and command registration. In `package.json`, contribute four command IDs and one `python2uml.generate` submenu under `explorer/context` for both files and folders. Do not duplicate extension lists in multiple TypeScript files.

- [ ] **Step 4: Compile and lint**

Run: `npm run compile`

Run: `npm run lint`

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add src/languages.ts src/filePicker.ts src/extension.ts src/umlGenerator.ts src/test/extension.test.ts package.json package-lock.json
git commit -m "feat: add language commands and Explorer menus"
```

### Task 10: First-Run Environment, Preview, Diagnostics, and Save As

**Files:**
- Modify: `src/pythonRunner.ts:1-50`
- Create: `src/previewPanel.ts`
- Modify: `src/umlGenerator.ts:1-120`
- Modify: `src/filePicker.ts:35-70`
- Modify: `src/extension.ts:40-100`
- Modify: `src/test/extension.test.ts`

**Interfaces:**
- `setupVenv(storageUri: vscode.Uri, extensionUri: vscode.Uri) -> Promise<string>` creates/reuses `storageUri/.venv` and runs `python -m pip install <extensionUri>` only when project metadata/version changed.
- `runScript(...) -> Promise<GenerationPayload>` parses the CLI JSON contract from Task 8.
- `showPreview(session: GenerationSession) -> vscode.WebviewPanel` displays SVG and diagnostics and emits a typed save message.

- [ ] **Step 1: Write tests for CLI JSON parsing, HTML escaping, save messages, and cleanup**

```typescript
test("preview escapes diagnostics", () => {
  const html = previewHtml("<svg></svg>", [{ message: "<script>alert(1)</script>" }]);
  assert.ok(!html.includes("<script>alert(1)</script>"));
  assert.ok(html.includes("&lt;script&gt;"));
});
```

Also assert that setup reuses an installed environment marker and that panel disposal deletes only its own temporary directory.

- [ ] **Step 2: Run compile/tests and verify failures**

Run: `npm run compile`

Run: `npm test`

Expected: FAIL until preview and JSON parsing helpers exist. If the VS Code harness cannot launch in the environment, record that separately; compilation/unit assertions must still pass.

- [ ] **Step 3: Implement the minimal preview/session flow**

Generate to a unique OS temporary directory. Use a restrictive webview content security policy, escape every diagnostic field, and handle only the literal message `{ command: "save" }`. Copy SVG directly; rerun Python for PNG/PDF/JPG/draw.io. Dispose cleanup must resolve and verify the target is inside the session temp directory before removal.

- [ ] **Step 4: Run extension verification**

Run: `npm run compile`

Run: `npm run lint`

Run: `npm test`

Expected: PASS, subject only to an explicitly documented unavailable GUI test harness.

- [ ] **Step 5: Commit**

```bash
git add src/pythonRunner.ts src/previewPanel.ts src/umlGenerator.ts src/filePicker.ts src/extension.ts src/test/extension.test.ts
git commit -m "feat: preview UML before saving"
```

### Task 11: Renderers, Documentation, AGENTS, and Full Verification

**Files:**
- Modify: `src/python/render/graphviz_renderer.py:1-80`
- Modify: `src/python/render/drawio_renderer.py:1-100`
- Modify: `README.md`
- Modify: `AGENTS.md` (ignored continuity file)
- Modify: `.gitignore` only if generated verification artifacts reveal a missing pattern.

**Interfaces:**
- Renderers consume only `UMLDiagram`; they never invent or resolve relationships.

- [ ] **Step 1: Add renderer assertions for all class kinds and relationship styles**

Extend `tests/test_renderers.py` to assert interface/abstract stereotypes, inheritance, implementation, association, aggregation, and composition in Graphviz source and draw.io XML without requiring visual pixel snapshots.

- [ ] **Step 2: Run renderer tests and fix only observed gaps**

Run: `python -m pytest tests/test_renderers.py -v`

Expected: PASS after both renderers map every current enum value.

- [ ] **Step 3: Update user and continuation documentation**

README must cover supported grammars, Python/pip first-run setup, Activity Bar/Command Palette/Explorer workflows, multi-selection, preview/save, source diagnostics, CLI usage, manual fixture inspection, external-type suppression, and heuristic limitations. Update ignored `AGENTS.md` from planned to verified file names, commands, and behavior.

- [ ] **Step 4: Run Black and full verification from a clean process**

Run: `python -m black --check src/python tests`

Run: `python -m pytest -v`

Run: `npm run compile`

Run: `npm run lint`

Run: `npm test`

Run: `git diff --check`

Expected: all available checks PASS; any unavailable VS Code GUI harness is reported with its exact error and is not described as passing.

- [ ] **Step 5: Commit final documentation and renderer changes**

```bash
git add README.md src/python/render/graphviz_renderer.py src/python/render/drawio_renderer.py tests/test_renderers.py .gitignore
git commit -m "docs: describe language-agnostic UML workflow"
```

- [ ] **Step 6: Review final repository state**

Run: `git status --short`

Confirm that only intentional user-owned pre-existing changes or ignored local artifacts remain, `AGENTS.md` is ignored, no `__pycache__` or generated diagrams are staged, and no manual regex parser survives:

Run: `rg -n "re\.|import re|from re import" src/python/parser`

Expected: no source-language parsing regex usage.
