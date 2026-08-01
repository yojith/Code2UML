#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime="$root/python-runtime"
licenses="$root/licenses"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT

rm -rf "$runtime" "$licenses"
uv python install --no-bin 3.12.10
source_python="$(uv python find --no-project --managed-python --no-python-downloads 3.12.10)"
source_prefix="$("$source_python" -c 'import sys; print(sys.prefix)')"
cp -a "$source_prefix" "$runtime"
license="$source_prefix/LICENSE.txt"
test -f "$license" || { echo "Missing bundled Python license: $license" >&2; exit 1; }
mkdir -p "$licenses/python"
cp "$license" "$licenses/python/LICENSE.txt"
runtime_python="$runtime/bin/python"
site_packages="$($runtime_python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
mkdir -p "$site_packages"

uv export --locked --no-dev --no-emit-project --output-file "$temporary/requirements.txt"
uv pip install --python "$runtime_python" --only-binary=:all: --requirement "$temporary/requirements.txt" --target "$site_packages"
uv pip install --python "$runtime_python" --no-deps --target "$site_packages" "$root"
find "$site_packages" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$site_packages" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
"$runtime_python" -c 'import python2uml, graphviz, tree_sitter'
