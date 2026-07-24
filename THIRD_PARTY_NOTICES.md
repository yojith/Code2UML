# Third-Party Notices

This notice applies to the generated Windows x64 extension package.

## Runtime provenance

- CPython 3.12.10 is taken from the official Windows embeddable archive: https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip (SHA-256 `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`). Its PSF license is packaged at `licenses/python/LICENSE.txt`. Only `python312._pth` is configured during assembly.
- Graphviz 15.0.0 is taken from the official Windows archive: https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/15.0.0/windows_10_cmake_Release_Graphviz-15.0.0-win64.zip (SHA-256 `778217b6e9f588310b21907be0525e8c3c6707b0ce0ad2be574a440fcc97cd29`). The complete runtime root is relocated without modifying its files.
- Graphviz project code is licensed under the Eclipse Public License 2.0. The exact upstream text is packaged at `licenses/graphviz/LICENSE`; corresponding source is available from https://gitlab.com/graphviz/graphviz/-/tree/15.0.0. Five separately licensed source/data artifacts incorporated into Graphviz binaries are listed below.
- Native dependency versions and notices come from Graphviz 15.0.0's exact `graphviz-windows-dependencies` gitlink, commit `ff985525b23a1a72ddb1a89482ea12233c3cbe85`: https://gitlab.com/graphviz/graphviz-windows-dependencies/-/tree/ff985525b23a1a72ddb1a89482ea12233c3cbe85. The release ZIP itself contains no license, copyright, notice, readme, manifest, or source inventory.

## Graphviz native inventory

The packaged files below are mapped to unmodified authoritative upstream license/copyright artifacts. The build script pins and verifies every artifact by SHA-256 before copying it into `licenses/graphviz/`.

| Component | Version | Bundled files | Packaged upstream material |
| --- | --- | --- | --- |
| Graphviz project code | 15.0.0 | All 35 executables; `cdt.dll`, `cgraph.dll`, `cgraph++.dll`, `gdtclft.dll`, `gvc.dll`, `gvc++.dll`, all `gvplugin_*.dll`, `gvpr.dll`, `pathplan.dll`, `tcldot*.dll`, `tclplan.dll`, `xdot.dll` | `LICENSE` |
| Graphviz rbtree code | Graphviz tag 15.0.0 snapshot | Linked into Graphviz libraries | `internal/rbtree-LICENSE` |
| Luc Maisonobe ellipse code | Graphviz tag 15.0.0 snapshot | Linked into Graphviz common library | `internal/ellipse.c` |
| ColorBrewer color schemes | Graphviz tag 15.0.0 snapshot | Generated into Graphviz color data | `internal/brewer_colors` |
| RandomKit/Mersenne Twister code | Graphviz tag 15.0.0 snapshot | Linked into Graphviz neatogen library | `internal/randomkit.c`, `internal/randomkit.h` |
| ANN | 1.1.2 | `ANN.dll` | `dependencies/ann-Copyright.txt`, `dependencies/ann-LGPL-2.1.txt`; corresponding source at `sources/ann_1.1.2.zip` |
| Brotli | 1.1.0 | `brotlicommon.dll`, `brotlidec.dll` | `dependencies/brotli.txt` |
| bzip2 | 1.0.8 | `bz2.dll` | `dependencies/bzip2.txt` |
| Cairo | 1.18.0 | `cairo-2.dll` | `dependencies/cairo.txt`, `spdx/cairo.json` |
| Expat | 2.6.2 | `libexpat.dll` | `dependencies/expat.txt` |
| Fontconfig | 2.14.2 | `fontconfig-1.dll` | `dependencies/fontconfig.txt` |
| FreeType | 2.13.2 | `freetype.dll` | `dependencies/freetype.txt` |
| FriBidi | 1.0.13 | `fribidi-0.dll` | `dependencies/fribidi.txt`, `spdx/fribidi.json` |
| getopt-win32 | 1.1.0.20220925 | `getopt.dll` | `dependencies/getopt-win32.txt`, `spdx/getopt-win32.json` |
| gettext/libintl | 0.22.5 | `intl-8.dll` | `dependencies/gettext-libintl.txt`, `spdx/gettext-libintl.json` |
| GLib | 2.78.4 | `gio-2.0-0.dll`, `glib-2.0-0.dll`, `gmodule-2.0-0.dll`, `gobject-2.0-0.dll` | `dependencies/glib.txt`, `spdx/glib.json` |
| GTS | 0.7.6 | `gts.dll` | `dependencies/gts.txt`, `spdx/gts.json` |
| HarfBuzz | 9.0.0 | `harfbuzz.dll` | `dependencies/harfbuzz.txt` |
| libffi | 3.4.6 | `ffi-8.dll` | `dependencies/libffi.txt` |
| libgd | 2.3.3 | `libgd.dll` | `dependencies/libgd.txt` |
| libiconv | 1.17 | `iconv-2.dll` | `dependencies/libiconv.txt`, `spdx/libiconv.json` |
| libjpeg-turbo | 3.0.1 | `jpeg62.dll` | `dependencies/libjpeg-turbo.txt` |
| XZ/liblzma | 5.4.4 | `liblzma.dll` | `dependencies/liblzma.txt` |
| libpng | 1.6.43 | `libpng16.dll` | `dependencies/libpng.txt` |
| libwebp | 1.4.0 | `libwebp.dll`, `libsharpyuv.dll` | `dependencies/libwebp.txt` |
| Pango | 1.50.14 | `pango-1.0-0.dll`, `pangocairo-1.0-0.dll`, `pangoft2-1.0-0.dll`, `pangowin32-1.0-0.dll` | `dependencies/pango.txt`, `spdx/pango.json` |
| PCRE2 | 10.43 | `pcre2-8.dll` | `dependencies/pcre2.txt` plus the full upstream `dependencies/pcre2-LICENCE` referenced by that file |
| pixman | 0.43.4 | `pixman-1-0.dll` | `dependencies/pixman.txt` |
| Tcl | 8.6.10-3 | `tcl86t.dll` | `dependencies/tcl.txt` |
| libtiff | 4.6.0 | `tiff.dll` | `dependencies/tiff.txt` |
| zlib | 1.3.1 | `zlib1.dll` | `dependencies/zlib.txt` |
| Microsoft Visual C++ Runtime | 14.44.35211.0 | `concrt140.dll`, `msvcp140.dll`, `msvcp140_1.dll`, `msvcp140_2.dll`, `msvcp140_atomic_wait.dll`, `msvcp140_codecvt_ids.dll`, `vcruntime140.dll`, `vcruntime140_1.dll` | `dependencies/msvc-runtime-license.docx` |

The `gts.txt` and `pango.txt` files are intentionally separate even though the exact upstream snapshot supplies byte-identical LGPL-2.0 texts for them.

This product includes color specifications and designs developed by Cynthia Brewer (http://colorbrewer.org/).

## Corresponding source

The packaged SPDX records identify the upstream source downloads and checksums recorded for Cairo, FriBidi, getopt-win32, gettext/libintl, GLib, GTS, libiconv, and Pango. ANN 1.1.2 source is included directly at `licenses/graphviz/sources/ann_1.1.2.zip`. No bundled third-party library was modified by this project.

**Pre-publication source requirement:** the Graphviz dependency snapshot does not include the exact vcpkg baseline, port recipes, patches, or source cache used to build these libraries. In addition, the recorded primary source URL for LGPL-3.0-only getopt-win32 1.1.0.20220925 is no longer available. Before distributing the extension, the publisher must obtain the original corresponding-source bundle and exact vcpkg build material, verify getopt-win32 against the recorded vcpkg SHA-512, host the complete bundle durably, and replace this paragraph with the required source-access or written-offer terms. The current inventory and URL list must not be represented as a complete corresponding-source offer.

## Microsoft Visual C++ Runtime

The eight Microsoft DLLs are unmodified version 14.44.35211.0 files. Their official version-pinned installer is https://download.visualstudio.microsoft.com/download/pr/1fd48b19-62fe-47d0-a030-f5fbb85dd5d9/CC0FF0EB1DC3F5188AE6300FAEF32BF5BEEBA4BDD6E8E445A9184072096B713B/VC_redist.x64.exe (SHA-256 `cc0ff0eb1dc3f5188ae6300faef32bf5beeba4bdd6e8e445a9184072096b713b`). Microsoft documents the Visual Studio 2022 REDIST list at https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution and app-local runtime deployment at https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170.

Redistribution of these files requires the extension publisher to hold a qualifying Visual Studio license and comply with its Distributable Code terms. The packaged Microsoft Visual C++ Runtime recipient license records recipient terms; it is not the publisher's redistribution grant. These files must not be distributed standalone.
