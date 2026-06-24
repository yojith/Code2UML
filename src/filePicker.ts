import { window } from "vscode";

export function uploadFiles(): Thenable<string[] | undefined> {
  const files = window.showOpenDialog({
    title: "Upload Python files",
    canSelectMany: true,
    filters: { "Python Files": ["py"] },
  });
  return files.then((uris) => {
    if (uris) {
      return uris.map((uri) => uri.fsPath);
    } else {
      return undefined;
    }
  });
}

export function uploadFolders(): Thenable<string[] | undefined> {
  const files = window.showOpenDialog({
    title: "Upload Python folders",
    canSelectFolders: true,
    canSelectMany: true,
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
