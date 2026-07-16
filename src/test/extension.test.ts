import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

// You can import and use all API from the 'vscode' module
// as well as import your extension to test it
import * as vscode from "vscode";
import { LANGUAGES } from "../languages";
import { resolveSelectedPaths } from "../umlGenerator";
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
});
