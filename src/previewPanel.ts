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
  return `<!DOCTYPE html>
<html><head>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}'">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>body{font-family:var(--vscode-font-family);color:var(--vscode-foreground)}svg{max-width:100%;height:auto}button{margin:1rem 0;padding:.5rem 1rem}</style>
</head><body>
<button id="save" type="button">Save As...</button>
<section aria-label="UML diagram">${svg}</section>
<h2>Analyzed documents</h2><ul>${documentItems || "<li>None</li>"}</ul>
<h2>Source diagnostics</h2><ul>${diagnosticItems || "<li>None</li>"}</ul>
<script nonce="${nonce}">const vscode=acquireVsCodeApi();document.getElementById('save').addEventListener('click',()=>vscode.postMessage({command:'save'}));</script>
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
