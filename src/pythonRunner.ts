import { execFile } from "child_process";
import { createHash } from "crypto";
import * as fs from "fs";
import * as path from "path";
import { promisify } from "util";
import { Uri } from "vscode";

type ProcessResult = { stdout: string | Buffer; stderr: string | Buffer };
type ProcessRunner = (executable: string, args: string[]) => Promise<ProcessResult>;
const execute = promisify(execFile) as unknown as ProcessRunner;

export interface SourceDiagnostic {
  path: string;
  line: number;
  column: number;
  severity: string;
  message: string;
}

export interface GenerationPayload {
  output: string;
  classes: Record<string, unknown>;
  relationships: unknown[];
  diagnostics: SourceDiagnostic[];
}

function projectMarker(extensionPath: string): string {
  const hash = createHash("sha256");
  for (const name of ["pyproject.toml", "package.json"]) {
    const metadata = path.join(extensionPath, name);
    if (fs.existsSync(metadata)) {
      hash.update(fs.readFileSync(metadata));
    }
  }
  return hash.digest("hex");
}

export async function setupVenv(
  storageUri: Uri,
  extensionUri: Uri,
  run: ProcessRunner = execute,
): Promise<string> {
  fs.mkdirSync(storageUri.fsPath, { recursive: true });
  const venvPath = Uri.joinPath(storageUri, ".venv").fsPath;
  const pythonExe = process.platform === "win32"
    ? path.join(venvPath, "Scripts", "python.exe")
    : path.join(venvPath, "bin", "python");
  const markerPath = path.join(venvPath, ".python2uml-project-marker");
  const marker = projectMarker(extensionUri.fsPath);

  const created = !fs.existsSync(pythonExe);
  if (created) {
    await run(process.platform === "win32" ? "python" : "python3", ["-m", "venv", venvPath]);
  }
  if (created || !fs.existsSync(markerPath) || fs.readFileSync(markerPath, "utf8") !== marker) {
    await run(pythonExe, ["-m", "pip", "install", extensionUri.fsPath]);
    fs.writeFileSync(markerPath, marker);
  }
  return pythonExe;
}

function isDiagnostic(value: unknown): value is SourceDiagnostic {
  if (!value || typeof value !== "object") {
    return false;
  }
  const item = value as Record<string, unknown>;
  return typeof item.path === "string"
    && typeof item.line === "number"
    && typeof item.column === "number"
    && typeof item.severity === "string"
    && typeof item.message === "string";
}

export function parseGenerationPayload(stdout: string): GenerationPayload {
  let value: unknown;
  try {
    value = JSON.parse(stdout);
  } catch {
    throw new Error("Python generator did not return valid JSON");
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Python generator returned a malformed payload");
  }
  const payload = value as Record<string, unknown>;
  if (typeof payload.output !== "string"
    || !payload.classes || typeof payload.classes !== "object" || Array.isArray(payload.classes)
    || !Array.isArray(payload.relationships)
    || !Array.isArray(payload.diagnostics) || !payload.diagnostics.every(isDiagnostic)) {
    throw new Error("Python generator returned a malformed payload");
  }
  return payload as unknown as GenerationPayload;
}

export async function runScript(
  pythonExec: string,
  pythonDir: Uri,
  args: string[],
): Promise<GenerationPayload> {
  const scriptPath = Uri.joinPath(pythonDir, "main.py").fsPath;
  try {
    const { stdout } = await execute(pythonExec, [scriptPath, ...args]);
    return parseGenerationPayload(String(stdout));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Python script failed: ${message}`);
  }
}
