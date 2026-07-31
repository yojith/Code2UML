import { execFile } from "child_process";
import * as fs from "fs";
import * as path from "path";
import { promisify } from "util";
import { env, Uri } from "vscode";

type ProcessResult = { stdout: string | Buffer; stderr: string | Buffer };
type ProcessOptions = { env: NodeJS.ProcessEnv; windowsHide: boolean };
type ProcessRunner = (executable: string, args: string[], options: ProcessOptions) => Promise<ProcessResult>;
const execute = promisify(execFile) as unknown as ProcessRunner;

export interface ExtensionRuntime {
  pythonExec: string;
  dotExec: string;
  env: NodeJS.ProcessEnv;
}

export const GRAPHVIZ_NOT_FOUND_MESSAGE = "Graphviz dot.exe was not found on PATH. Install Graphviz for Windows, add its bin directory to PATH, then restart VS Code.";

export interface SourceDiagnostic {
  path: string;
  line: number;
  column: number;
  severity: string;
  message: string;
}

export interface GenerationPayload {
  output: string;
  documents: string[];
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

function requireFile(filePath: string, label: string): void {
  try {
    if (fs.statSync(filePath).isFile()) {
      return;
    }
  } catch {}
  throw new Error(`${label} was not found: ${filePath}`);
}

function requireVisualCppRuntime(systemRoot: string | undefined): void {
  const systemDirectory = systemRoot ? path.join(systemRoot, "System32") : "";
  const requiredFiles = ["vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"];
  if (systemDirectory && requiredFiles.every((file) => fs.existsSync(path.join(systemDirectory, file)))) {
    return;
  }
  throw new Error("Code2UML requires the Microsoft Visual C++ 2015-2022 Redistributable x64. Install it from https://aka.ms/vs/17/release/vc_redist.x64.exe and restart VS Code.");
}

export function resolveGraphvizOnPath(pathValue = process.env.PATH ?? ""): string {
  for (const directory of pathValue.split(path.delimiter)) {
    const dotExec = path.join(directory, "dot.exe");
    try {
      if (fs.statSync(dotExec).isFile()) {
        return dotExec;
      }
    } catch {}
  }
  throw new Error(GRAPHVIZ_NOT_FOUND_MESSAGE);
}

export function resolveRuntime(
  extensionUri: Uri,
  platform = process.platform,
  architecture = process.arch,
  remoteName = env.remoteName,
  systemRoot = process.env.SystemRoot ?? process.env.WINDIR,
  graphvizPath = process.env.PATH ?? "",
): ExtensionRuntime {
  if (remoteName) {
    throw new Error(`Code2UML currently supports only local Windows x64 extension hosts; detected remote host ${remoteName} on ${platform}-${architecture}`);
  }
  if (platform !== "win32" || architecture !== "x64") {
    throw new Error(`Code2UML currently supports only Windows x64; detected ${platform}-${architecture}`);
  }
  const extensionPath = `${extensionUri.fsPath[0].toUpperCase()}${extensionUri.fsPath.slice(1)}`;
  const pythonExec = path.join(extensionPath, "python-runtime", "python.exe");
  requireFile(pythonExec, "Bundled Python executable");
  requireVisualCppRuntime(systemRoot);
  const dotExec = resolveGraphvizOnPath(graphvizPath);
  const runtimeEnv = {
    ...process.env,
    PATH: process.env.PATH,
    PYTHONNOUSERSITE: "1",
    PYTHONUNBUFFERED: "1",
  };
  return {
    pythonExec,
    dotExec,
    env: runtimeEnv,
  };
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
    || !Array.isArray(payload.documents) || !payload.documents.every((document) => typeof document === "string")
    || !isRecord(payload.classes) || !Object.values(payload.classes).every(isSerializedClass)
    || !Array.isArray(payload.relationships) || !payload.relationships.every(isRelationship)
    || !Array.isArray(payload.diagnostics) || !payload.diagnostics.every(isDiagnostic)) {
    throw new Error("Python generator returned a malformed payload");
  }
  return payload as unknown as GenerationPayload;
}

export async function runScript(
  runtime: ExtensionRuntime,
  args: string[],
  run: ProcessRunner = execute,
): Promise<GenerationPayload> {
  let stdout: string | Buffer;
  try {
    ({ stdout } = await run(runtime.pythonExec, ["-m", "python2uml", ...args], {
      env: runtime.env,
      windowsHide: true,
    }));
  } catch (error) {
    const processError = error as { code?: unknown; stderr?: string | Buffer };
    const message = error instanceof Error ? error.message : String(error);
    const stderr = processError.stderr ? String(processError.stderr).trim() : "";
    const outputIndex = args.findIndex((argument) => argument === "-o" || argument === "--output");
    const outputFormat = outputIndex >= 0 ? path.extname(args[outputIndex + 1] ?? "").slice(1).toLowerCase() || "unknown" : "unknown";
    throw new Error(`Python script failed using ${runtime.pythonExec} for ${outputFormat} output on ${process.platform}-${process.arch} (exit code ${String(processError.code ?? "unknown")}): ${stderr || message}`);
  }
  return parseGenerationPayload(String(stdout));
}
