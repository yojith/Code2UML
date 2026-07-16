import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

// You can import and use all API from the 'vscode' module
// as well as import your extension to test it
import * as vscode from "vscode";
import { LANGUAGES } from "../languages";
import { resolveSelectedPaths } from "../umlGenerator";
import { parseGenerationPayload, setupVenv } from "../pythonRunner";
import {
  cleanupSession,
  isSaveMessage,
  previewHtml,
  savePreview,
} from "../previewPanel";
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
    const manifest = require("../../package.json");

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
          "../..",
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
  });

  test("setup creates once and reuses the matching project marker", async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "python2uml-setup-"));
    const storage = vscode.Uri.file(path.join(root, "storage"));
    const extension = vscode.Uri.file(path.join(root, "extension"));
    fs.mkdirSync(extension.fsPath);
    fs.writeFileSync(path.join(extension.fsPath, "pyproject.toml"), '[project]\nversion = "1"\n');
    const calls: Array<{ executable: string; args: string[] }> = [];
    const execute = async (executable: string, args: string[]) => {
      calls.push({ executable, args });
      if (args[0] === "-m" && args[1] === "venv") {
        const python = process.platform === "win32"
          ? path.join(args[2], "Scripts", "python.exe")
          : path.join(args[2], "bin", "python");
        fs.mkdirSync(path.dirname(python), { recursive: true });
        fs.writeFileSync(python, "");
      }
      return { stdout: "", stderr: "" };
    };
    try {
      const first = await setupVenv(storage, extension, execute);
      const second = await setupVenv(storage, extension, execute);
      assert.strictEqual(first, second);
      assert.strictEqual(calls.length, 2);
      assert.deepStrictEqual(calls[1], {
        executable: first,
        args: ["-m", "pip", "install", extension.fsPath],
      });
      fs.writeFileSync(path.join(extension.fsPath, "pyproject.toml"), '[project]\nversion = "2"\n');
      await setupVenv(storage, extension, execute);
      assert.strictEqual(calls.length, 3);
      assert.deepStrictEqual(calls[2], calls[1]);
    } finally {
      fs.rmSync(root, { recursive: true });
    }
  });

  test("preview escapes diagnostics, restricts messages, and labels documents", () => {
    const html = previewHtml("<svg></svg>", ["safe.py"], [
      { path: "<bad>", line: 1, column: 2, severity: "error", message: "<script>alert(1)</script>" },
    ]);
    assert.ok(!html.includes("<script>alert(1)</script>"));
    assert.ok(html.includes("&lt;script&gt;"));
    assert.ok(html.includes("Content-Security-Policy"));
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
