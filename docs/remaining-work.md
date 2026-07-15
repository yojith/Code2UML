# python2uml Remaining Work Handoff

## Why This File Exists

Work paused on 2026-07-14 to conserve the user's ChatGPT credits. Resume from this file and `AGENTS.md`; do not repeat the completed architecture/design discussion.

## Safe Checkpoint

- Branch: `main` (user explicitly approved in-place work).
- Committed HEAD: `b7ada2a` (`fix: classify each C declarator`).
- Approved design: `docs/superpowers/specs/2026-07-14-language-agnostic-uml-and-vscode-workflow-design.md`.
- Implementation plan: `docs/superpowers/plans/2026-07-14-language-agnostic-uml-and-vscode-workflow.md`.
- Ignored durable ledger: `.superpowers/sdd/progress.md`.
- Tasks 1-6 are complete and independently reviewed. Do not redo them.

## Completed Architecture

- Python uses standard-library `ast` through `src/python/parser/python_parser.py`.
- Java, C++, and C use official Tree-sitter grammar packages through dedicated adapters.
- `src/python/parser/abstracter.py` is a small dispatcher.
- All parsers emit `NormalizedModule` dataclasses and source diagnostics.
- Analyzers consume only normalized dataclasses and never read source/parser-native nodes.
- External type names remain visible in signatures but never become nodes or edges.
- Relationship evidence is deterministic: composition > aggregation > association.
- `pyproject.toml` owns runtime/dev dependencies and Black line length 200.
- Task 6's final full Python run before its last narrow reviewed fix was 46 passed; its final focused C run was 7 passed and the reviewer approved it.

## Completed Commits

```text
8a66924 build: define normalized parser contracts
f181eaa feat: infer relationships from normalized evidence
e9c0686 test: strengthen normalized analyzer coverage
7a7e1f2 refactor: isolate Python AST adapter
1d3dea0 fix: preserve Python parser semantics
b8416cd fix: retain setter ownership evidence
a40f236 feat: parse Java with Tree-sitter
3857499 fix: normalize Java relationship evidence
c484ea4 fix: ignore shadowed Java collection fields
4c153bb feat: parse C++ with Tree-sitter
efcabf9 fix: link C++ declarations across files
ffb37a3 fix: preserve C++ method qualifiers
15858eb fix: normalize C++ signature endpoints
58dd1ec fix: canonicalize C++ parameter qualifiers
8d76099 feat: model C projects with Tree-sitter
e421c10 fix: normalize guarded C declarations
b7ada2a fix: classify each C declarator
```

## Current Dirty Worktree Warning

The checkout was already dirty before implementation. Never reset, clean, checkout, or discard broadly.

Task 7 currently has uncommitted changes in these areas:

- `tests/test_fixture_projects.py`: new ignored/untracked parametrized test with eight exact project cases; force-add it when ready.
- `src/test/python/project2/system.py`: `User` now inherits `Entity, Repository`.
- `src/test/java/project1/Shop.java`: constructor stores a supplied `Product` member to exercise aggregation.
- `src/test/cpp/project2/system.hpp`: `Entity` has protected state so it is abstract, `Repository` follows `Entity`, and `Team` currently has `User* lead`.
- All four `src/test/{python,java,cpp,c}` trees are still untracked as a group and contain pre-existing user fixture work plus Task 7 edits.

Other dirty files existed before Task 7 and must be preserved, including README/package/extension/render/loader changes and local artifacts shown by `git status --short`.

## Resume Task 7 First

Last verified fixture run before the final C++ fixture edits:

```text
8 collected: 5 passed, 3 failed
```

The three failures at that time were:

1. Java project2 had an additional `User -> Entity` association from `save(Entity)` alongside inheritance. Decide whether that association is correct evidence (likely include it in the exact expectation) or change the fixture only if the method is not intended.
2. C++ project2 had Repository/Entity ordering and Team/User ownership mismatches plus an additional User/Entity association. The current inspected fixture already contains the attempted `Repository` reorder and `User* lead`; rerun before changing anything.
3. C project1 behavior was correct; only expected class-list ordering differed (`shop_c` sorted before `shop_h`). Fix deterministic expected ordering, not parser behavior.

First command on resume (use the exact venv interpreter, never bare `python`):

```powershell
& 'C:\Users\yojit\Documents\Yojith_Work\Yojith_Coding\python2uml\.venv\Scripts\python.exe' -m pytest -p no:cacheprovider tests\test_fixture_projects.py -vv
```

Then finish Task 7 requirements:

- Make all eight exact fixture cases green.
- Ensure every `project2` exercises all applicable relationships, nesting, abstract/interface behavior, and implementation.
- Update `src/python/analyze_test_projects.py` to accept `--language {python,java,cpp,c}` and include diagnostics in JSON.
- Add a failing inspector test before changing the helper.
- Split/replace `tests/test_project_loader_and_graphviz.py` into focused loader and renderer tests as planned.
- Run the manual inspector once per language and parse its output as valid JSON.
- Black every modified Python file.
- Run full pytest.
- Commit Task 7, create `.superpowers/sdd/task-7-report.md`, generate a review package, and obtain an independent task review.

## Tasks 8-11 Still Unstarted

### Task 8: Generator/CLI Result Protocol

- Add `AnalysisResult` with diagram and diagnostics.
- Separate analyze from render.
- Make CLI stdout one JSON object for the extension preview.
- Preserve partial models with clearly separated source diagnostics.
- Add CLI/generator pytest coverage first.

### Task 9: VS Code Commands and Context Menus

- Add one `src/languages.ts` metadata table.
- Expose Python, Java, C++, and C commands in Activity Bar and Command Palette.
- Add identical `Generate UML for...` submenus for file and folder Explorer contexts.
- Support multi-selection; filter/deduplicate compatible resources and warn for skipped inputs.
- Keep file pickers restricted by language extension.

### Task 10: First-Run Environment and Preview/Save

- Create/reuse `.venv` and install `pyproject.toml` runtime dependencies with pip on first run.
- Use a temporary SVG, not an immediate save dialog.
- Show a safe VS Code webview with diagram, source diagnostics, and `Save As...`.
- Copy SVG directly; rerender other Graphviz formats/draw.io.
- Clean only the session temp directory on dispose.

### Task 11: Renderers, Docs, and Verification

- Assert every class-kind stereotype and relationship style in both renderers.
- Update README and final `AGENTS.md` to verified behavior.
- Run Black check, full pytest, TypeScript compile, ESLint, VS Code tests, and `git diff --check`.
- Search parser directory to confirm no source-language regex parser remains.
- Perform a broad final code review and branch-finishing workflow.

## Exact Tool Paths / Environment Notes

- Always use `C:\Users\yojit\Documents\Yojith_Work\Yojith_Coding\python2uml\.venv\Scripts\python.exe` for Python, pip, pytest, and Black commands.
- The venv currently uses Python 3.12.13. Python 3.12.5 was rejected by Black due its known memory-safety issue.
- Pytest may warn that `.pytest_cache` is unwritable; use `-p no:cacheprovider` for clean focused runs.
- Sandboxed PATH hid Node/npm, but the host paths were verified:
  - Node: `C:\Users\yojit\AppData\Local\nvm\v25.2.1\node.exe`
  - npm: `C:\Users\yojit\AppData\Local\nvm\v25.2.1\npm.cmd`
- Run npm outside the sandbox or with the explicit npm path if `npm` is not found.
- New files under `tests/` are ignored by a local `tests/.gitignore` containing `*`; use `git add -f` for intentional new test files.

## Formatting and Review Rules

- Black every Python file modified, using the configured line length 200.
- Follow RED -> verify failure -> minimal GREEN -> verify pass.
- Keep changes task-scoped and commit after each approved task.
- Preserve all user-owned dirty files.
- Do not add regex source parsing, confidence scoring, external placeholder UML nodes, or compiler toolchain dependencies.
