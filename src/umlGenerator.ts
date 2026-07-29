import * as vscode from "vscode";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { uploadFiles, saveFile } from "./filePicker";
import { LANGUAGES, LanguageId } from "./languages";
import { resolveBundledRuntime, runScript } from "./pythonRunner";
import { cleanupSession, savePreview, showPreview } from "./previewPanel";

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

export async function generateUML(
  context: vscode.ExtensionContext,
  language: LanguageId,
  clicked?: vscode.Uri,
  selected?: vscode.Uri[],
) {
  let tempDir: string | undefined;
  try {
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

    vscode.window.showInformationMessage("Launching UML generator...");
    const runtime = resolveBundledRuntime(context.extensionUri);
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "python2uml-preview-"));
    const svgPath = path.join(tempDir, "preview.svg");
    const baseArgs = ["-t", language, "-p", ...paths];

    try {
      const payload = await runScript(runtime, ["-t", language, "-o", svgPath, "-p", ...paths]);
      showPreview({
        tempDir,
        svgPath,
        documents: payload.documents,
        payload,
        save: async () => {
          const destination = await saveFile();
          if (!destination) {
            return;
          }
          await savePreview(svgPath, destination, async () => {
            await runScript(runtime, ["-o", destination, ...baseArgs]);
          });
          vscode.window.showInformationMessage("UML diagram saved successfully!");
        },
      }, context.extensionUri);
      tempDir = undefined;
    } catch (error) {
      vscode.window.showErrorMessage(
        `Error: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  } catch (error) {
    vscode.window.showErrorMessage(
      `Error: ${error instanceof Error ? error.message : String(error)}`,
    );
  } finally {
    if (tempDir) {
      cleanupSession(tempDir, path.join(tempDir, "preview.svg"));
    }
  }
}
