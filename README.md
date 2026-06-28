# python2uml

Convert Python, Java, C++, and C source code into UML-style diagrams directly in VS Code.
Note: Graphviz must be installed.

## Features

- Generate UML diagrams from Python, Java, C++, and C files or folders
- Support Graphviz output plus draw.io (`.drawio`) export
- Clean, orthogonal diagram layout
- Select save location via native file dialog

## Usage

### Generate UML from Files

1. Open the command palette (`Ctrl+Shift+P`)
2. Run `python2uml: Generate UML Diagram from Python Files`
3. Select source file(s)
4. Choose a save location and output format
5. View your UML diagram

### Generate UML from Folders

1. Open the command palette (`Ctrl+Shift+P`)
2. Run `python2uml: Generate UML Diagram from Python Folders`
3. Select folder(s) containing source files
4. Choose a save location and output format
5. View your UML diagram

## C / C++ / Java Modeling Notes

- Java and C++ are treated as source entities with class, interface, enum, and abstract-class detection.
- Inner classes are emitted with qualified names such as `Outer.Inner`.
- C has no classes, so the renderer treats each file as a container node and emits detected `struct` and `enum` declarations as separate nodes.
- This is a pragmatic UML-style view, not a full language semantic model.

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
