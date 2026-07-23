import { randomBytes } from "crypto";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";
import { GenerationPayload, SourceDiagnostic } from "./pythonRunner";

export interface GenerationSession {
  tempDir: string;
  svgPath: string;
  documents: string[];
  payload: GenerationPayload;
  save: () => Promise<void>;
}

function escapeHtml(value: unknown): string {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function previewHtml(
  svg: string,
  documents: string[],
  diagnostics: SourceDiagnostic[],
): string {
  const nonce = randomBytes(16).toString("hex");
  const documentItems = documents.map((document) => `<li>${escapeHtml(document)}</li>`).join("");
  const diagnosticItems = diagnostics.map((diagnostic) =>
    `<li>${escapeHtml(diagnostic.severity)}: ${escapeHtml(diagnostic.path)}:${escapeHtml(diagnostic.line)}:${escapeHtml(diagnostic.column)} - ${escapeHtml(diagnostic.message)}</li>`,
  ).join("");
  const documentLabel = `${documents.length} ${documents.length === 1 ? "document" : "documents"}`;
  const diagnosticLabel = `${diagnostics.length} ${diagnostics.length === 1 ? "diagnostic" : "diagnostics"}`;
  const diagnosticState = diagnostics.length === 0 ? "success" : diagnostics.some(({ severity }) => severity === "error") ? "error" : "warning";
  return `<!DOCTYPE html>
<html lang="en"><head>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}'">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
:root{color-scheme:light dark}
*{box-sizing:border-box}
body{margin:0;padding:0;color:var(--vscode-editor-foreground);background:var(--vscode-editor-background);font-family:var(--vscode-font-family);font-size:var(--vscode-font-size);line-height:1.4}
.preview-shell{min-height:100vh;display:flex;flex-direction:column}
.preview-toolbar{position:sticky;top:0;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 20px;border-bottom:1px solid var(--vscode-panel-border);background:var(--vscode-sideBar-background,var(--vscode-editor-background))}
.preview-heading{min-width:0}
.preview-title{margin:0;font-size:15px;font-weight:600;line-height:1.3}
.preview-subtitle{margin:2px 0 0;color:var(--vscode-descriptionForeground);font-size:12px}
.preview-actions{display:flex;align-items:center;gap:10px;flex-shrink:0}
.preview-status{font-size:12px;color:var(--vscode-descriptionForeground)}
.preview-status.error{color:var(--vscode-errorForeground)}
.preview-status.warning{color:var(--vscode-editorWarning-foreground)}
.preview-status.success{color:var(--vscode-testing-iconPassed)}
button{border:1px solid var(--vscode-button-border,transparent);border-radius:2px;padding:6px 12px;color:var(--vscode-button-foreground);background:var(--vscode-button-background);font:inherit;cursor:pointer}
button:hover{background:var(--vscode-button-hoverBackground)}
button:focus-visible,summary:focus-visible{outline:1px solid var(--vscode-focusBorder);outline-offset:2px}
.diagram-scroll{flex:1;overflow:auto;padding:24px clamp(16px,4vw,48px)}
.diagram-frame{width:fit-content;min-width:min(100%,640px);margin:0 auto;padding:24px;background:var(--vscode-editorWidget-background,var(--vscode-editor-background));border:1px solid var(--vscode-widget-border,var(--vscode-panel-border));border-radius:4px;box-shadow:0 2px 8px var(--vscode-widget-shadow,transparent)}
.diagram-frame svg{display:block;max-width:none;height:auto}
.preview-details{margin:0 20px 12px;border:1px solid var(--vscode-panel-border);border-radius:3px;background:var(--vscode-sideBar-background,var(--vscode-editor-background))}
.preview-details summary{padding:8px 12px;color:var(--vscode-foreground);cursor:pointer;font-weight:600;list-style-position:inside}
.preview-details ul{margin:0;padding:0 16px 12px 32px;color:var(--vscode-descriptionForeground)}
.preview-details li{margin:4px 0;overflow-wrap:anywhere}
.preview-count{margin-left:4px;color:var(--vscode-descriptionForeground);font-weight:400}
@media(max-width:600px){.preview-toolbar{align-items:flex-start;flex-direction:column}.preview-actions{width:100%;justify-content:space-between}.diagram-scroll{padding:16px}.preview-details{margin-left:16px;margin-right:16px}}
</style>
</head><body>
<main class="preview-shell">
<header class="preview-toolbar">
  <div class="preview-heading"><h1 class="preview-title">UML Preview</h1><p class="preview-subtitle">${escapeHtml(documentLabel)}</p></div>
  <div class="preview-actions"><span class="preview-status ${diagnosticState}" aria-live="polite">${escapeHtml(diagnosticLabel)}</span><button id="save" type="button" aria-label="Save UML diagram" title="Save UML diagram">Save As…</button></div>
</header>
<section class="diagram-scroll" aria-label="UML diagram"><div class="diagram-frame">${svg}</div></section>
<details class="preview-details"><summary>Analyzed documents <span class="preview-count">${escapeHtml(documentLabel)}</span></summary><ul>${documentItems || "<li>None</li>"}</ul></details>
<details class="preview-details"${diagnostics.length > 0 ? " open" : ""}><summary>Source diagnostics <span class="preview-count">${escapeHtml(diagnosticLabel)}</span></summary><ul>${diagnosticItems || "<li>None</li>"}</ul></details>
</main>
<script nonce="${nonce}">const vscode=acquireVsCodeApi();document.getElementById("save")?.addEventListener("click",()=>vscode.postMessage({command:"save"}));</script>
</body></html>`;
}

export function isSaveMessage(value: unknown): value is { command: "save" } {
  return !!value
    && typeof value === "object"
    && !Array.isArray(value)
    && Object.keys(value).length === 1
    && (value as Record<string, unknown>).command === "save";
}

export async function savePreview(
  svgPath: string,
  destination: string,
  rerender: () => Promise<void>,
): Promise<void> {
  if (path.extname(destination).toLowerCase() === ".svg") {
    fs.copyFileSync(svgPath, destination);
    return;
  }
  await rerender();
}

export function cleanupSession(tempDir: string, svgPath: string): void {
  const resolvedDir = fs.realpathSync(tempDir);
  const resolvedSvg = path.resolve(svgPath);
  const relative = path.relative(resolvedDir, resolvedSvg);
  if (path.dirname(resolvedDir) !== fs.realpathSync(os.tmpdir())
    || !path.basename(resolvedDir).startsWith("python2uml-preview-")
    || relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("Refusing to clean an unverified preview session");
  }
  fs.rmSync(resolvedDir, { recursive: true, force: true });
}

export function showPreview(session: GenerationSession): vscode.WebviewPanel {
  const panel = vscode.window.createWebviewPanel(
    "python2uml.preview",
    "UML Preview",
    vscode.ViewColumn.Active,
    { enableScripts: true, localResourceRoots: [] },
  );
  panel.webview.html = previewHtml(
    fs.readFileSync(session.svgPath, "utf8"),
    session.documents,
    session.payload.diagnostics,
  );
  panel.webview.onDidReceiveMessage(async (message: unknown) => {
    if (isSaveMessage(message)) {
      try {
        await session.save();
      } catch (error) {
        vscode.window.showErrorMessage(`Error: ${error instanceof Error ? error.message : String(error)}`);
      }
    }
  });
  panel.onDidDispose(() => cleanupSession(session.tempDir, session.svgPath));
  return panel;
}
