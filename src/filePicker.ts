import { window } from "vscode";
import { LANGUAGES, LanguageId } from "./languages";

export function uploadFiles(language: LanguageId): Thenable<string[] | undefined> {
  const metadata = LANGUAGES.find(({ id }) => id === language)!;
  const files = window.showOpenDialog({
    title: `Select ${metadata.label} source files or folders`,
    canSelectFiles: true,
    canSelectFolders: true,
    canSelectMany: true,
    filters: { [`${metadata.label} Files`]: [...metadata.extensions] },
  });
  return files.then((uris) => {
    if (uris) {
      return uris.map((uri) => uri.fsPath);
    } else {
      return undefined;
    }
  });
}

export function saveFile(): Thenable<string | undefined> {
  const file = window.showSaveDialog({
    title: "Save UML Diagram",
    filters: {
      "SVG files": ["svg"],
      "PNG files": ["png"],
      "PDF files": ["pdf"],
      "JPG files": ["jpg", "jpeg"],
      "draw.io files": ["drawio"],
    },
  });
  return file.then((uri) => {
    if (uri) {
      return uri.fsPath;
    } else {
      return undefined;
    }
  });
}
