# Third-Party Notices

This notice applies to the generated Windows x64 extension package.

## Runtime provenance

- CPython 3.12.10 is from the official embeddable archive and its PSF license is packaged at `licenses/python/LICENSE.txt`.
- Graphviz 15.0.0 is built from source by vcpkg commit `000cc974fe23a0232f92abd3af8cf83b7ea9cbbb`, triplet `x64-windows`, with the `tools` feature. The official Graphviz Windows ZIP is not packaged.
- The generated package includes `licenses/graphviz/vcpkg/`: the exact installed-package status, every installed port recipe and patch, source downloads, the vcpkg commit, and provenance metadata. Package copyright, license, notice, and SPDX files are copied from the installed `share/` tree to `licenses/graphviz/share/`.
- `scripts/graphviz-msvc-stdalign.diff` is applied to the Graphviz port. It replaces unavailable `<stdalign.h>` includes with MSVC's `_Alignof` spelling; the applied patch is archived with the port recipe.
- The runtime contains no Microsoft VC runtime DLLs. Microsoft Visual C++ 2015-2022 Redistributable x64 is a system prerequisite.

## Source and license access

The VSIX contains the license/provenance material above. Before public distribution, publish the archived vcpkg source-download and port-material bundle at a durable URL and add that URL here, including any corresponding-source or written-offer terms required by the bundled dependency licenses.
