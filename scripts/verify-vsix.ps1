[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Vsix,
    [Parameter(Mandatory)][string]$Target
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$python = if ($Target.StartsWith('win32-')) { 'extension/python-runtime/python.exe' } else { 'extension/python-runtime/bin/python' }
$archive = [IO.Compression.ZipFile]::OpenRead((Resolve-Path $Vsix))
try {
    $entries = @($archive.Entries.FullName)
    $required = 'extension/out/src/extension.js', 'extension/package.json', 'extension/media/python2uml.svg', 'extension/media/python2uml.png', 'extension/media/codicons/codicon.css', 'extension/media/codicons/codicon.ttf', $python, 'extension/licenses/python/LICENSE.txt', 'extension/THIRD_PARTY_NOTICES.md'
    $required | ForEach-Object { if ($entries -cnotcontains $_) { throw "Missing required VSIX entry: $_" } }
    $forbidden = $entries | Where-Object { $_.StartsWith('extension/src/') -or $_.StartsWith('extension/build/') -or $_.StartsWith('extension/scripts/') -or $_ -in 'extension/pyproject.toml', 'extension/uv.lock', 'extension/python-runtime/Lib/site-packages/.lock' -or ($_ -split '/' | Where-Object { $_ -in '.venv', '.git', '__pycache__', 'tests' }) }
    if ($forbidden) { throw "Forbidden VSIX entries:`n$($forbidden -join "`n")" }
} finally { $archive.Dispose() }
