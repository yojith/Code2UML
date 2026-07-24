[CmdletBinding()]
param([string]$BuildPython)

$pythonUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
$pythonSha256 = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'
$graphvizUrl = 'https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/15.0.0/windows_10_cmake_Release_Graphviz-15.0.0-win64.zip'
$graphvizSha256 = '778217b6e9f588310b21907be0525e8c3c6707b0ce0ad2be574a440fcc97cd29'
$graphvizLicenseUrl = 'https://gitlab.com/graphviz/graphviz/-/raw/15.0.0/LICENSE'
$graphvizLicenseSha256 = '0becf16567beb77fa252b7664631dd177c8f9a1889e48995b45379c7130e5303'

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$BuildPython = if ($BuildPython) { $BuildPython } else { Join-Path $repositoryRoot '.venv\Scripts\python.exe' }
$pythonRuntime = Join-Path $repositoryRoot 'python-runtime'
$graphvizRuntime = Join-Path $repositoryRoot 'graphviz'
$licenses = Join-Path $repositoryRoot 'licenses'

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'Runtime assembly supports only Windows x64.'
}
if (-not (Test-Path -LiteralPath $BuildPython -PathType Leaf)) {
    throw "Build-time Python was not found: $BuildPython"
}

function Remove-GeneratedDirectory([string]$Path) {
    if ([IO.Path]::GetFullPath((Split-Path -Parent $Path)) -ne $repositoryRoot) {
        throw "Refusing to remove path outside the repository root: $Path"
    }
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Get-VerifiedDownload([string]$Uri, [string]$Sha256, [string]$Destination) {
    Invoke-WebRequest -Uri $Uri -OutFile $Destination
    $actual = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $Sha256) {
        throw "Checksum mismatch for $Uri. Expected $Sha256; got $actual."
    }
}

$temporary = Join-Path ([IO.Path]::GetTempPath()) ("python2uml-runtime-" + [guid]::NewGuid())
$environmentNames = 'PATH', 'EXTENSION_GRAPHVIZ_DOT', 'PYTHONNOUSERSITE', 'PYTHONUNBUFFERED'
$savedEnvironment = @{}
foreach ($name in $environmentNames) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
New-Item -ItemType Directory -Path $temporary | Out-Null
Push-Location $repositoryRoot
try {
    Remove-GeneratedDirectory $pythonRuntime
    Remove-GeneratedDirectory $graphvizRuntime
    Remove-GeneratedDirectory $licenses
    New-Item -ItemType Directory -Path $pythonRuntime, $graphvizRuntime, (Join-Path $licenses 'python'), (Join-Path $licenses 'graphviz') | Out-Null

    $pythonArchive = Join-Path $temporary 'python.zip'
    $graphvizArchive = Join-Path $temporary 'graphviz.zip'
    $graphvizExtract = Join-Path $temporary 'graphviz-extracted'
    $requirements = Join-Path $temporary 'requirements.txt'
    Get-VerifiedDownload $pythonUrl $pythonSha256 $pythonArchive
    Get-VerifiedDownload $graphvizUrl $graphvizSha256 $graphvizArchive
    Expand-Archive -LiteralPath $pythonArchive -DestinationPath $pythonRuntime
    Expand-Archive -LiteralPath $graphvizArchive -DestinationPath $graphvizExtract

    $pth = Join-Path $pythonRuntime 'python312._pth'
    $pthContent = (Get-Content -LiteralPath $pth -Raw).Replace('#import site', "Lib/site-packages`r`nimport site")
    Set-Content -LiteralPath $pth -Value $pthContent -NoNewline -Encoding ascii

    & uv export --frozen --no-dev --no-emit-project --output-file $requirements
    if ($LASTEXITCODE -ne 0) { throw 'uv export failed.' }
    $sitePackages = Join-Path $pythonRuntime 'Lib\site-packages'
    & $BuildPython -m pip install --only-binary=:all: --requirement $requirements --target $sitePackages
    if ($LASTEXITCODE -ne 0) { throw 'Production dependency installation failed.' }
    & $BuildPython -m pip install --no-deps --target $sitePackages $repositoryRoot
    if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed.' }

    $dot = Get-ChildItem -LiteralPath $graphvizExtract -Filter dot.exe -File -Recurse | Where-Object { $_.Directory.Name -eq 'bin' } | Select-Object -First 1
    if (-not $dot) { throw 'dot.exe was not found in the Graphviz archive.' }
    Copy-Item -Path (Join-Path $dot.Directory.Parent.FullName '*') -Destination $graphvizRuntime -Recurse
    Copy-Item -LiteralPath (Join-Path $pythonRuntime 'LICENSE.txt') -Destination (Join-Path $licenses 'python\LICENSE.txt')
    Get-VerifiedDownload $graphvizLicenseUrl $graphvizLicenseSha256 (Join-Path $licenses 'graphviz\LICENSE')

    $bundledPython = Join-Path $pythonRuntime 'python.exe'
    $bundledDot = Join-Path $graphvizRuntime 'bin\dot.exe'
    [Environment]::SetEnvironmentVariable('EXTENSION_GRAPHVIZ_DOT', $bundledDot, 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONNOUSERSITE', '1', 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONUNBUFFERED', '1', 'Process')
    [Environment]::SetEnvironmentVariable('PATH', "$(Split-Path -Parent $bundledDot)$([IO.Path]::PathSeparator)$env:PATH", 'Process')

    & $bundledPython -c 'import python2uml, graphviz, tree_sitter'
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Python import smoke test failed.' }
    & $bundledDot -V
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Graphviz version smoke test failed.' }
    $smokeOutput = Join-Path $temporary 'smoke.svg'
    & $bundledPython -m python2uml -t python -o $smokeOutput -p (Join-Path $repositoryRoot 'tests\fixtures\python\project1')
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $smokeOutput)) { throw 'Backend SVG smoke test failed.' }
    if ((Get-Content -LiteralPath $smokeOutput -Raw) -notmatch '<svg') { throw 'Backend smoke output is not SVG.' }

    Get-ChildItem -LiteralPath $sitePackages -Directory -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $sitePackages -File -Recurse | Where-Object { $_.Extension -in '.pyc', '.pyo' } | Remove-Item -Force
}
finally {
    Pop-Location
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
    if (Test-Path -LiteralPath $temporary) {
        Remove-Item -LiteralPath $temporary -Recurse -Force
    }
}
