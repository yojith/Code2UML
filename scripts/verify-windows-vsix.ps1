[CmdletBinding()]
param([Parameter(Mandatory)][string]$Vsix)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead((Resolve-Path $Vsix))
try {
    $entries = @($archive.Entries.FullName)
    $required = 'extension/out/src/extension.js', 'extension/package.json', 'extension/media/python2uml.svg', 'extension/media/codicons/codicon.css', 'extension/media/codicons/codicon.ttf', 'extension/media/codicons/LICENSE', 'extension/media/codicons/LICENSE-CODE', 'extension/python-runtime/python.exe', 'extension/python-runtime/Lib/site-packages/python2uml/__init__.py', 'extension/python-runtime/Lib/site-packages/graphviz/__init__.py', 'extension/python-runtime/Lib/site-packages/tree_sitter_c/_binding.pyd', 'extension/python-runtime/Lib/site-packages/tree_sitter_cpp/_binding.pyd', 'extension/python-runtime/Lib/site-packages/tree_sitter_java/_binding.pyd', 'extension/graphviz/bin/dot.exe', 'extension/licenses/python/LICENSE.txt', 'extension/licenses/graphviz/LICENSE', 'extension/third-party-source-provenance/graphviz/vcpkg/commit.txt', 'extension/third-party-source-provenance/graphviz/vcpkg/provenance.json', 'extension/third-party-source-provenance/graphviz/vcpkg/downloads/graphviz-graphviz-15.0.0.tar.gz', 'extension/third-party-source-provenance/graphviz/vcpkg/ports/graphviz/msvc-stdalign.diff', 'extension/third-party-source-provenance/graphviz/vcpkg/installed/vcpkg/status', 'extension/third-party-source-provenance/graphviz/vcpkg/installed/vcpkg/info/graphviz_15.0.0_x64-windows.list', 'extension/third-party-source-provenance/graphviz/vcpkg/buildtrees/graphviz/x64-windows.vcpkg_abi_info.txt', 'extension/THIRD_PARTY_NOTICES.md'
    $required | ForEach-Object { if ($entries -cnotcontains $_) { throw "Missing required VSIX entry: $_" } }
    foreach ($prefix in 'extension/graphviz/lib/', 'extension/graphviz/share/', 'extension/licenses/graphviz/share/', 'extension/third-party-source-provenance/graphviz/vcpkg/ports/', 'extension/third-party-source-provenance/graphviz/vcpkg/downloads/', 'extension/third-party-source-provenance/graphviz/vcpkg/installed/vcpkg/info/', 'extension/third-party-source-provenance/graphviz/vcpkg/buildtrees/') {
        if (-not ($entries | Where-Object { $_.StartsWith($prefix, [StringComparison]::Ordinal) })) { throw "Missing required VSIX prefix: $prefix" }
    }
    $forbiddenDll = 'vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'concrt140.dll', 'ucrtbase.dll'
    $forbidden = foreach ($entry in $entries) {
        if ($entry.StartsWith('extension/src/') -or $entry.StartsWith('extension/build/') -or $entry.StartsWith('extension/scripts/') -or $entry -in 'extension/pyproject.toml', 'extension/uv.lock', 'extension/python-runtime/Lib/site-packages/.lock' -or ($entry -split '/' | Where-Object { $_ -in '.venv', '.git', '__pycache__', 'tests' })) { $entry; continue }
        if ($entry.StartsWith('extension/graphviz/') -and ($forbiddenDll | Where-Object { $entry.EndsWith($_, [StringComparison]::OrdinalIgnoreCase) })) { $entry }
    }
    if ($forbidden) { throw "Forbidden VSIX entries:`n$($forbidden -join "`n")" }
} finally { $archive.Dispose() }
