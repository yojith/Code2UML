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
  classes: Record<string, SerializedClass>;
  relationships: SerializedRelationship[];
  diagnostics: SourceDiagnostic[];
}

type ClassKind = "class" | "abstract_class" | "interface" | "enum" | "struct" | "file" | "module";
type RelationshipType = "inheritance" | "implementation" | "association" | "aggregation" | "composition";

export interface SerializedAttribute {
  name: string;
  type_name: string | null;
  visibility: string;
}

export interface SerializedMethod {
  name: string;
  parameters: string[];
  return_type: string | null;
  visibility: string;
}

export interface SerializedClass {
  name: string;
  kind: ClassKind;
  attributes: SerializedAttribute[];
  methods: SerializedMethod[];
}

export interface SerializedRelationship {
  source: string;
  target: string;
  relationship_type: RelationshipType;
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function nullableString(value: unknown): boolean {
  return value === null || typeof value === "string";
}

function isAttribute(value: unknown): value is SerializedAttribute {
  if (!isRecord(value)) {
    return false;
  }
  return typeof value.name === "string"
    && nullableString(value.type_name)
    && typeof value.visibility === "string";
}

function isMethod(value: unknown): value is SerializedMethod {
  if (!isRecord(value)) {
    return false;
  }
  return typeof value.name === "string"
    && Array.isArray(value.parameters) && value.parameters.every((parameter) => typeof parameter === "string")
    && nullableString(value.return_type)
    && typeof value.visibility === "string";
}

function isSerializedClass(value: unknown): value is SerializedClass {
  if (!isRecord(value)) {
    return false;
  }
  return typeof value.name === "string"
    && typeof value.kind === "string"
    && ["class", "abstract_class", "interface", "enum", "struct", "file", "module"].includes(value.kind)
    && Array.isArray(value.attributes) && value.attributes.every(isAttribute)
    && Array.isArray(value.methods) && value.methods.every(isMethod);
}

function isRelationship(value: unknown): value is SerializedRelationship {
  if (!isRecord(value)) {
    return false;
  }
  return typeof value.source === "string"
    && typeof value.target === "string"
    && typeof value.relationship_type === "string"
    && ["inheritance", "implementation", "association", "aggregation", "composition"].includes(value.relationship_type);
}

function isDiagnostic(value: unknown): value is SourceDiagnostic {
  if (!isRecord(value)) {
    return false;
  }
  const item = value;
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
    || !isRecord(payload.classes) || !Object.values(payload.classes).every(isSerializedClass)
    || !Array.isArray(payload.relationships) || !payload.relationships.every(isRelationship)
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
