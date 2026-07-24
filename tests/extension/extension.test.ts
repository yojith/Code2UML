import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

// You can import and use all API from the 'vscode' module
// as well as import your extension to test it
import * as vscode from "vscode";
import { LANGUAGES } from "../../src/languages";
import { resolveSelectedPaths } from "../../src/umlGenerator";
import { parseGenerationPayload, resolveBundledRuntime, runScript } from "../../src/pythonRunner";
import {
  cleanupSession,
  isSaveMessage,
  previewHtml,
  savePreview,
} from "../../src/previewPanel";
// import * as myExtension from '../../extension';

suite("Extension Test Suite", () => {
  vscode.window.showInformationMessage("Start all tests.");

  test("defines every supported language once", () => {
    assert.deepStrictEqual(
      LANGUAGES.map(({ id, extensions, commandId }) => ({
        id,
        extensions,
        commandId,
      })),
      [
        {
          id: "python",
          extensions: ["py"],
          commandId: "python2uml.generatePython",
        },
        {
          id: "java",
          extensions: ["java"],
          commandId: "python2uml.generateJava",
        },
        {
          id: "cpp",
          extensions: ["cpp", "cc", "cxx", "hpp", "hh", "h"],
          commandId: "python2uml.generateCpp",
        },
        {
          id: "c",
          extensions: ["c", "h"],
          commandId: "python2uml.generateC",
        },
      ],
    );
  });

  test("contributes one shared Explorer submenu", () => {
    const manifest = require("../../../package.json");

    assert.deepStrictEqual(manifest.contributes.menus["explorer/context"], [
      {
        submenu: "python2uml.generate",
        when: "resourceScheme == file",
        group: "navigation",
      },
    ]);
    assert.deepStrictEqual(
      manifest.contributes.menus["python2uml.generate"].map(
        ({ command }: { command: string }) => command,
      ),
      LANGUAGES.map(({ commandId }) => commandId),
    );
    assert.ok(
      fs.existsSync(
        path.resolve(
          __dirname,
          "../../..",
          manifest.contributes.viewsContainers.activitybar[0].icon,
        ),
      ),
    );
  });

  test("resolves compatible multi-selection and reports incompatible files", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "python2uml-"));
    try {
      const project = vscode.Uri.file(path.join(root, "project.v2"));
      const pythonFile = vscode.Uri.file(path.join(root, "model.py"));
      const incompatibleFile = vscode.Uri.file(path.join(root, "model.java"));
      const extensionlessFile = vscode.Uri.file(path.join(root, "README"));
      fs.mkdirSync(project.fsPath);
      for (const uri of [pythonFile, incompatibleFile, extensionlessFile]) {
        fs.writeFileSync(uri.fsPath, "");
      }

      assert.deepStrictEqual(
        resolveSelectedPaths("python", pythonFile, [
          project,
          pythonFile,
          incompatibleFile,
          project,
          extensionlessFile,
        ]),
        {
          paths: [project.fsPath, pythonFile.fsPath],
          skipped: [incompatibleFile.fsPath, extensionlessFile.fsPath],
        },
      );
    } finally {
      fs.rmSync(root, { recursive: true });
    }
  });

  test("parses the single CLI JSON payload and rejects noisy output", () => {
    const json = JSON.stringify({
      output: "diagram.svg",
      classes: {},
      relationships: [],
      diagnostics: [
        { path: "bad.py", line: 2, column: 3, severity: "error", message: "bad" },
      ],
    });
    assert.strictEqual(parseGenerationPayload(json).output, "diagram.svg");
    assert.throws(() => parseGenerationPayload(`noise\n${json}`), /valid JSON/);
    assert.throws(() => parseGenerationPayload('{"output":1}'), /payload/);
    assert.throws(() => parseGenerationPayload(JSON.stringify({
      output: "diagram.svg",
      classes: { Broken: { name: 1, kind: "class", attributes: [], methods: [] } },
      relationships: [],
      diagnostics: [],
    })), /payload/);
    assert.throws(() => parseGenerationPayload(JSON.stringify({
      output: "diagram.svg",
      classes: {},
      relationships: [{ source: "A", target: "B", relationship_type: "owns" }],
      diagnostics: [],
    })), /payload/);
  });

  test("invokes the installed Python module", async () => {
    const runtime = {
      pythonExec: "python",
      dotExec: "dot",
      env: { TEST_RUNTIME: "1" },
    };
    const calls: Array<{ executable: string; args: string[]; options: { env: NodeJS.ProcessEnv; windowsHide: boolean } }> = [];
    const run = async (executable: string, args: string[], options: { env: NodeJS.ProcessEnv; windowsHide: boolean }) => {
      calls.push({ executable, args, options });
      return { stdout: JSON.stringify({ output: "diagram.drawio", classes: {}, relationships: [], diagnostics: [] }), stderr: "" };
    };
    await runScript(runtime, ["-t", "java", "-o", "diagram.drawio", "-p", "Model.java"], run);
    assert.deepStrictEqual(calls, [{
      executable: "python",
      args: ["-m", "python2uml", "-t", "java", "-o", "diagram.drawio", "-p", "Model.java"],
      options: { env: runtime.env, windowsHide: true },
    }]);
  });

  test("reports process rejection diagnostics", async () => {
    const runtime = {
      pythonExec: "C:\\runtime\\python.exe",
      dotExec: "C:\\graphviz\\dot.exe",
      env: {},
    };
    const run = async () => {
      throw Object.assign(new Error("process failed"), {
        code: 7,
        stderr: "runtime failure\n",
      });
    };

    await assert.rejects(
      runScript(runtime, [], run),
      {
        message: `Python script failed using C:\\runtime\\python.exe on ${process.platform}-${process.arch} (exit code 7): runtime failure`,
      },
    );
  });

  test("resolves an isolated bundled Windows runtime", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "python2uml runtime "));
    const extension = vscode.Uri.file(root);
    const python = path.join(root, "python-runtime", "python.exe");
    const dot = path.join(root, "graphviz", "bin", "dot.exe");
    fs.mkdirSync(path.dirname(python), { recursive: true });
    fs.mkdirSync(path.dirname(dot), { recursive: true });
    fs.writeFileSync(python, "");
    fs.writeFileSync(dot, "");
    const parentPath = process.env.PATH;
    try {
      const runtime = resolveBundledRuntime(extension, "win32", "x64");
      assert.strictEqual(runtime.pythonExec, python);
      assert.strictEqual(runtime.dotExec, dot);
      assert.strictEqual(runtime.env.EXTENSION_GRAPHVIZ_DOT, dot);
      assert.strictEqual(runtime.env.PYTHONNOUSERSITE, "1");
      assert.strictEqual(runtime.env.PYTHONUNBUFFERED, "1");
      assert.strictEqual(runtime.env.PATH?.split(path.delimiter)[0], path.dirname(dot));
      assert.strictEqual(process.env.PATH, parentPath);
    } finally {
      fs.rmSync(root, { recursive: true });
    }
  });

  test("rejects unsupported hosts and missing runtimes", () => {
    const extension = vscode.Uri.file(path.join(os.tmpdir(), "missing-runtime"));
    assert.throws(() => resolveBundledRuntime(extension, "linux", "x64"), /only Windows x64.*linux-x64/);
    assert.throws(() => resolveBundledRuntime(extension, "win32", "arm64"), /only Windows x64.*win32-arm64/);
    assert.throws(() => resolveBundledRuntime(extension, "win32", "x64"), /python\.exe/);
  });

  test("preview escapes diagnostics, restricts messages, and labels documents", () => {
    const html = previewHtml("<svg></svg>", ["safe.py"], [
      { path: "<bad>", line: 1, column: 2, severity: "error", message: "<script>alert(1)</script>" },
    ]);
    assert.ok(!html.includes("<script>alert(1)</script>"));
    assert.ok(html.includes("&lt;script&gt;"));
    assert.ok(html.includes("Content-Security-Policy"));
    assert.ok(html.includes('class="preview-toolbar"'));
    assert.ok(html.includes('aria-label="Save UML diagram"'));
    assert.ok(html.includes("Analyzed documents"));
    assert.ok(html.includes("1 document"));
    assert.ok(html.includes("1 diagnostic"));
    assert.ok(html.includes("<details"));
    assert.ok(html.includes("Analyzed documents"));
    assert.ok(html.includes("Source diagnostics"));
    assert.strictEqual(isSaveMessage({ command: "save" }), true);
    assert.strictEqual(isSaveMessage({ command: "save", extra: true }), false);
    assert.strictEqual(isSaveMessage({ command: "delete" }), false);
  });

  test("cleanup removes only the verified session directory", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "python2uml-cleanup-"));
    const session = fs.mkdtempSync(path.join(os.tmpdir(), "python2uml-preview-"));
    const sibling = path.join(root, "keep.txt");
    const crafted = path.join(root, "python2uml-preview-crafted");
    fs.writeFileSync(sibling, "keep");
    fs.mkdirSync(crafted);
    const craftedSvg = path.join(crafted, "preview.svg");
    fs.writeFileSync(craftedSvg, "<svg></svg>");
    assert.throws(() => cleanupSession(crafted, craftedSvg), /session/);
    assert.ok(fs.existsSync(crafted));
    cleanupSession(session, path.join(session, "preview.svg"));
    assert.ok(!fs.existsSync(session));
    assert.ok(fs.existsSync(sibling));
    assert.throws(() => cleanupSession(root, sibling), /session/);
    fs.rmSync(root, { recursive: true });
  });

  test("save copies SVG and rerenders other formats", async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "python2uml-save-"));
    const preview = path.join(root, "preview.svg");
    const svg = path.join(root, "saved.svg");
    const png = path.join(root, "saved.png");
    fs.writeFileSync(preview, "<svg>preview</svg>");
    let rerenders = 0;
    try {
      await savePreview(preview, svg, async () => { rerenders += 1; });
      assert.strictEqual(fs.readFileSync(svg, "utf8"), "<svg>preview</svg>");
      assert.strictEqual(rerenders, 0);
      await savePreview(preview, png, async () => { rerenders += 1; });
      assert.strictEqual(rerenders, 1);
      assert.ok(!fs.existsSync(png));
    } finally {
      fs.rmSync(root, { recursive: true });
    }
  });
});
