// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from "vscode";
import { generateUML } from "./umlGenerator";
import { LANGUAGES } from "./languages";

class UMLActionItem extends vscode.TreeItem {
  constructor(
    label: string,
    commandId: string,
    description: string,
  ) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.description = description;
    this.command = { command: commandId, title: label };
  }
}

class UMLActionsProvider implements vscode.TreeDataProvider<UMLActionItem> {
  private readonly items = LANGUAGES.map(
    ({ label, commandId }) =>
      new UMLActionItem(`Generate UML for ${label}`, commandId, label),
  );

  getTreeItem(element: UMLActionItem): vscode.TreeItem {
    return element;
  }

  getChildren(): UMLActionItem[] {
    return this.items;
  }
}

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
  // Use the console to output diagnostic information (console.log) and errors (console.error)
  // This line of code will only be executed once when your extension is activated
  console.log('Congratulations, your extension "python2uml" is now active!');

  // The command has been defined in the package.json file
  // Now provide the implementation of the command with registerCommand
  // The commandId parameter must match the command field in package.json
  const commands = LANGUAGES.map(({ id, commandId }) =>
    vscode.commands.registerCommand(
      commandId,
      (clicked?: vscode.Uri, selected?: vscode.Uri[]) =>
        generateUML(context, id, clicked, selected),
    ),
  );

  const treeView = vscode.window.createTreeView("python2uml.actions", {
    treeDataProvider: new UMLActionsProvider(),
    showCollapseAll: false,
  });

  context.subscriptions.push(...commands, treeView);
}

// This method is called when your extension is deactivated
export function deactivate() {}
