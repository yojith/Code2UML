# python2uml

Convert Python source code into UML class diagrams directly in VS Code.
Note: Graphviz must be installed.

## Features

- Generate UML diagrams from Python files or folders
- Support multiple output formats: SVG, PDF, PNG, JPG
- Clean, orthogonal diagram layout
- Select save location via native file dialog

## Usage

### Generate UML from Files

1. Open the command palette (`Ctrl+Shift+P`)
2. Run `python2uml: Generate UML Diagram from Python Files`
3. Select Python file(s)
4. Choose a save location and output format
5. View your UML diagram

### Generate UML from Folders

1. Open the command palette (`Ctrl+Shift+P`)
2. Run `python2uml: Generate UML Diagram from Python Folders`
3. Select folder(s) containing Python files
4. Choose a save location and output format
5. View your UML diagram

## Requirements

- Python 3.x
- Graphviz

### Install Graphviz

1. Download the installer from the official site: <https://graphviz.org/download/>
2. Run the installer
3. Check "Add Graphviz to PATH" during install (critical)
4. Restart your terminal / VS Code

## License

MIT
