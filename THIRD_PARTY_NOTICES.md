# Third-Party Notices

This notice applies to the generated Windows x64 extension package.

## Runtime provenance

- CPython 3.12.10 is from the official Windows x64 embeddable archive at https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip (SHA-256 `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`). Its PSF license is packaged at `licenses/python/LICENSE.txt`; only `python312._pth` is configured during assembly.
- Graphviz 15.0.0 is built from source by vcpkg commit `000cc974fe23a0232f92abd3af8cf83b7ea9cbbb`, triplet `x64-windows`, with the `tools` feature. The official Graphviz Windows ZIP is not packaged.
- Binary caching is disabled for the vcpkg build. The generated package includes `third-party-source-provenance/graphviz/vcpkg/`: every installed port recipe and patch, every direct source/download archive retained by the build, installed-package status and file metadata, ABI build metadata, the vcpkg commit, and provenance metadata. Extracted build-tool working trees are not packaged. Package copyright, license, notice, and SPDX files are copied from the installed `share/` tree to `licenses/graphviz/share/`.
- `scripts/graphviz-msvc-stdalign.diff` is applied to the Graphviz port. It replaces unavailable `<stdalign.h>` includes with MSVC's `_Alignof` spelling; the applied patch is archived with the port recipe.
- The runtime contains no Microsoft VC runtime DLLs. Microsoft Visual C++ 2015-2022 Redistributable x64 is a system prerequisite.

## Preview assets

- Microsoft Codicons 0.0.36 (`media/codicons/`) provides the locally packaged preview toolbar stylesheet and font. The stylesheet/code is licensed under the MIT License at `media/codicons/LICENSE-CODE`; the font is licensed under Creative Commons Attribution 4.0 International at `media/codicons/LICENSE`.

## Source and license access

The VSIX contains the exact vcpkg source downloads, port material, applied patches, build metadata, installed-file inventory, and upstream license/provenance material described above under `third-party-source-provenance/graphviz/`.
