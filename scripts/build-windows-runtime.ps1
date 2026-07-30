[CmdletBinding()]
param([string]$BuildPython)

$pythonUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
$pythonSha256 = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$BuildPython = if ($BuildPython) { $BuildPython } else { Join-Path $repositoryRoot '.venv\Scripts\python.exe' }
$BuildPython = [IO.Path]::GetFullPath($BuildPython)
$pythonRuntime = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'python-runtime'))
$licenses = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'licenses'))
$allowedGeneratedPaths = $pythonRuntime, $licenses

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'Runtime assembly supports only Windows x64.'
}
if (-not (Test-Path -LiteralPath $BuildPython -PathType Leaf)) {
    throw "Build-time Python was not found: $BuildPython"
}

function New-Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Remove-GeneratedDirectory([string]$Path) {
    $normalizedPath = [IO.Path]::GetFullPath($Path)
    if ($normalizedPath -notin $allowedGeneratedPaths) {
        throw "Refusing to remove unexpected generated path: $Path"
    }
    if (Test-Path -LiteralPath $normalizedPath) {
        $target = Get-Item -LiteralPath $normalizedPath -Force
        if (-not $target.PSIsContainer -or ($target.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Refusing to remove unsafe generated path: $normalizedPath"
        }
        Remove-Item -LiteralPath $normalizedPath -Recurse -Force
    }
}

function Get-Sha256([string]$Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try {
        ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $stream.Dispose()
        $algorithm.Dispose()
    }
}

function Get-VerifiedDownload([string]$Uri, [string]$Sha256, [string]$Destination) {
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $Destination
    $actual = Get-Sha256 $Destination
    if ($actual -ne $Sha256) {
        throw "Checksum mismatch for $Uri. Expected $Sha256; got $actual."
    }
}

$temporary = Join-Path ([IO.Path]::GetTempPath()) ("python2uml-runtime-" + [guid]::NewGuid())
New-Directory $temporary
Push-Location $repositoryRoot
try {
    Remove-GeneratedDirectory $pythonRuntime
    Remove-GeneratedDirectory $licenses
    New-Directory $pythonRuntime
    New-Directory (Join-Path $licenses 'python')

    $pythonArchive = Join-Path $temporary 'python.zip'
    $requirements = Join-Path $temporary 'requirements.txt'
    Get-VerifiedDownload $pythonUrl $pythonSha256 $pythonArchive
    Expand-Archive -LiteralPath $pythonArchive -DestinationPath $pythonRuntime

    $pth = Join-Path $pythonRuntime 'python312._pth'
    $pthContent = (Get-Content -LiteralPath $pth -Raw).Replace('#import site', "Lib/site-packages`r`nimport site")
    Set-Content -LiteralPath $pth -Value $pthContent -NoNewline -Encoding ascii
    Get-ChildItem -LiteralPath $pythonRuntime -File | Where-Object { $_.Name -match '^(vcruntime|msvcp|concrt|ucrtbase).*\.dll$' } | Remove-Item -Force

    & uv export --locked --no-dev --no-emit-project --output-file $requirements
    if ($LASTEXITCODE -ne 0) { throw 'uv export failed.' }
    $sitePackages = Join-Path $pythonRuntime 'Lib\site-packages'
    & uv pip install --python $BuildPython --only-binary=:all: --requirement $requirements --target $sitePackages
    if ($LASTEXITCODE -ne 0) { throw 'Production dependency installation failed.' }
    & uv pip install --python $BuildPython --no-deps --target $sitePackages $repositoryRoot
    if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed.' }

    $targetLock = Join-Path $sitePackages '.lock'
    if (Test-Path -LiteralPath $targetLock) { Remove-Item -LiteralPath $targetLock -Force }
    Copy-Item -LiteralPath (Join-Path $pythonRuntime 'LICENSE.txt') -Destination (Join-Path $licenses 'python\LICENSE.txt') -Force

    & (Join-Path $pythonRuntime 'python.exe') -c 'import python2uml, graphviz, tree_sitter'
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Python import smoke test failed.' }
    Get-ChildItem -LiteralPath $sitePackages -Directory -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $sitePackages -File -Recurse | Where-Object { $_.Extension -in '.pyc', '.pyo' } | Remove-Item -Force
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $temporary) {
        Remove-Item -LiteralPath $temporary -Recurse -Force
    }
}
