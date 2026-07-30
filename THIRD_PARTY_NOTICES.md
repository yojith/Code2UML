# Third-Party Notices

This notice applies to the generated Windows x64 extension package.

## Bundled runtime provenance

- CPython 3.12.10 is from the official Windows x64 embeddable archive at https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip (SHA-256 `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`). Its PSF license is packaged at `licenses/python/LICENSE.txt`; only `python312._pth` is configured during assembly.
- The runtime contains no Microsoft VC runtime DLLs. Microsoft Visual C++ 2015-2022 Redistributable x64 is a system prerequisite.

## Preview assets

- Microsoft Codicons 0.0.36 (`media/codicons/`) provides the locally packaged preview toolbar stylesheet and font. The stylesheet/code is licensed under the MIT License at `media/codicons/LICENSE-CODE`; the font is licensed under Creative Commons Attribution 4.0 International at `media/codicons/LICENSE`.

Graphviz is not bundled. Users install Graphviz separately and make `dot.exe` available on `PATH`.
