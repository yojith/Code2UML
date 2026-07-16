import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { uploadFiles, saveFile } from "./filePicker";
import { LANGUAGES, LanguageId } from "./languages";
import { setupVenv, runScript } from "./pythonRunner";

export function resolveSelectedPaths(
  language: LanguageId,
  clicked?: vscode.Uri,
  selected?: vscode.Uri[],
): { paths: string[]; skipped: string[] } {
  const compatible = new Set(
    LANGUAGES.find(({ id }) => id === language)!.extensions.map(
      (extension) => `.${extension}`,
    ),
  );
  const paths: string[] = [];
  const skipped: string[] = [];

  for (const uri of [...(selected ?? []), ...(clicked ? [clicked] : [])]) {
    if (paths.includes(uri.fsPath) || skipped.includes(uri.fsPath)) {
      continue;
    }
    try {
      const extension = path.extname(uri.fsPath).toLowerCase();
      (fs.statSync(uri.fsPath).isDirectory() || compatible.has(extension)
        ? paths
        : skipped
      ).push(uri.fsPath);
    } catch {
      skipped.push(uri.fsPath);
    }
  }

  return { paths, skipped };
}

function resolveGeneratedOutputPath(outputPath: string): string {
  if (path.extname(outputPath)) {
    return outputPath;
  }
  return `${outputPath}.svg`;
}

export async function generateUML(
  context: vscode.ExtensionContext,
  language: LanguageId,
  clicked?: vscode.Uri,
  selected?: vscode.Uri[],
) {
  try {
    const venvPython = await setupVenv(context.extensionUri);
    const resolved = resolveSelectedPaths(language, clicked, selected);
    if (resolved.skipped.length) {
      vscode.window.showWarningMessage(
        `Skipped incompatible resources: ${resolved.skipped.join(", ")}`,
      );
    }
    const paths = clicked || selected ? resolved.paths : await uploadFiles(language);
    if (!paths || paths.length === 0) {
      vscode.window.showWarningMessage("No files or folders were selected.");
      return;
    }

    const outputPath = await saveFile();
    if (!outputPath) {
      vscode.window.showWarningMessage("No output file was selected.");
      return;
    }

    vscode.window.showInformationMessage("Launching UML generator...");

    const args = ["-t", language, "-o", outputPath, "-p", ...paths];
    const pythonDir = vscode.Uri.joinPath(
      context.extensionUri,
      "src",
      "python",
    );

    try {
      const output = await runScript(venvPython, pythonDir, args);
      console.log(output);
      vscode.window.showInformationMessage(
        "UML diagram generated successfully!",
      );
      await vscode.commands.executeCommand(
        "vscode.open",
        vscode.Uri.file(resolveGeneratedOutputPath(outputPath)),
      );
    } catch (error) {
      vscode.window.showErrorMessage(
        `Error: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  } catch (error) {
    vscode.window.showErrorMessage(
      `Error: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}
