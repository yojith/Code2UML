# Code2UML

[![Build](https://github.com/yojith/Code2UML/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/yojith/Code2UML/actions/workflows/build.yml) [![VS Code Marketplace](https://img.shields.io/badge/VS%20Code%20Marketplace-Code2UML-007ACC?logo=visualstudiocode&logoColor=white)](https://marketplace.visualstudio.com/items?itemName=yojith.python2uml) [![License](https://img.shields.io/github/license/yojith/Code2UML)](https://github.com/yojith/Code2UML/blob/main/LICENSE.txt)

Generate UML diagrams from Python, Java, C++, and C projects.

## Use it in VS Code

Install Code2UML from the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=yojith.python2uml). Then you can:

- Open the **Code2UML** icon in the Activity Bar and choose a language.
- Press `Ctrl+Shift+P` and run **Generate UML for...**.
- Right-click a file or folder in Explorer and choose **Generate UML for...**.

The preview can save diagrams as SVG, PNG, PDF, JPG, or draw.io files.

## Requirements

The packaged extension supports Windows x64, Linux x64/ARM64, and macOS x64/Apple Silicon. Each platform package includes its own Python runtime, so you do not need to install Python or pip.

Install [Graphviz](https://graphviz.org/download/), add the directory containing `dot` (`dot.exe` on Windows) to `PATH`, and restart VS Code. Code2UML uses Graphviz to lay out and render diagrams.

## Command line

The CLI is available from a source checkout. It accepts one project type (`python`, `java`, `cpp`, or `c`) and one or more files or folders:

```powershell
& .\.venv\Scripts\python.exe -m python2uml --project-type java --output diagram.svg --paths tests\fixtures\java\project1
```

Graphviz must also be available on `PATH` when using the CLI.

## Developer build

The extension's Python runtime is generated into `python-runtime/` and packaged with the VSIX. Build the runtime for your host platform with:

```powershell
npm run build:runtime:win32-x64
# or build:runtime:linux-x64, build:runtime:linux-arm64,
# build:runtime:darwin-x64, build:runtime:darwin-arm64
```

Then compile or package the extension with the normal npm scripts.

## License

MIT
