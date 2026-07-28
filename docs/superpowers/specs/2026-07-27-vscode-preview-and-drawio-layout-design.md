# VS Code Preview and Draw.io Layout Design

## Goal

Improve the VS Code UML preview's navigation and provenance display, and replace draw.io's custom grid layout with Graphviz-derived, editable orthogonal geometry.

## Scope

### Preview

- The SVG opens at fit-to-width.
- The toolbar provides labelled Codicon buttons for zoom out, fit width, zoom in, and reset, alongside the existing Save action.
- Button zoom keeps the visual viewport centre stable. Ctrl+wheel zoom keeps the point below the pointer stable.
- The preview uses local Codicon assets and VS Code webview CSS theme tokens. It does not load a stylesheet, font, or script from the network and does not add a UI framework.
- The CLI payload includes the absolute paths of the source files actually collected for analysis. The preview's Analyzed documents section renders those paths.

### Draw.io

- Draw.io generation runs the configured bundled `dot` executable with deterministic `dot` layout and JSON geometry output.
- The Graphviz input uses the draw.io cell dimensions for every node, treats every relationship identically for layout, and requests orthogonal splines.
- The renderer converts Graphviz's coordinates, perimeter attachment points, and bend points to draw.io `mxGeometry` values. It preserves the existing UML compartments and relationship-specific arrow styles.
- The existing hierarchy/alphabetical grid is removed with no layout fallback.
- A missing/invalid bundled executable or unusable Graphviz geometry fails draw.io generation with a clear error. SVG rendering remains unchanged.

## Architecture

The Python analysis result retains the collected source-file paths and serializes them in the CLI JSON payload. The extension validates this list and passes it to the preview instead of the initial selection.

The draw.io renderer has a small Graphviz-layout adapter: it emits a fixed-size DOT graph, invokes the existing configured `dot.exe`, parses `-Tjson` geometry, transforms Graphviz's lower-left coordinate system to draw.io's upper-left coordinate system, and then creates ordinary editable mxGraph cells and edges. Graphviz determines geometry only; draw.io continues to own rendering and relationship arrow styling.

The webview uses native buttons, theme tokens, local Codicon CSS/font assets, and a short inline script for pan-preserving scale changes. No framework or external resource is added.

## Error Handling

- A malformed CLI payload, including a non-string source-file path, is rejected by the extension.
- Draw.io generation reports whether Graphviz could not run, did not return JSON, omitted a node, or did not supply usable edge geometry.
- The preview buttons remain keyboard accessible, have explicit labels/tooltips, and do not change the existing save-message validation boundary.

## Verification

- TypeScript tests cover payload path validation and preview markup/controls.
- Python tests use deterministic JSON fixtures/mocks to cover coordinate conversion, parallel edges, self-loops, special-character node names, variable dimensions, invalid geometry, and repeatable output.
- A real Graphviz draw.io smoke test runs where the bundled runtime is available; CI installs/uses Graphviz before tests that invoke it.
- Existing Python, TypeScript, lint, VS Code extension, and packaging checks remain green.

## Constraints

- Keep the source-built, pinned-vcpkg Graphviz runtime and its compliance/provenance workflow unchanged.
- Do not bundle Microsoft VC runtime DLLs.
- Do not change SVG renderer layout behaviour.
- Do not broadly restructure workflows, packaging, or unrelated scripts.
