[CmdletBinding()]
param([string]$BuildPython)

$pythonUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
$pythonSha256 = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'
$vcpkgCommit = '000cc974fe23a0232f92abd3af8cf83b7ea9cbbb'
$vcpkgRepositoryUrl = 'https://github.com/microsoft/vcpkg.git'

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
Set-StrictMode -Version Latest

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$BuildPython = if ($BuildPython) { $BuildPython } else { Join-Path $repositoryRoot '.venv\Scripts\python.exe' }
$BuildPython = [IO.Path]::GetFullPath($BuildPython)
$pythonRuntime = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'python-runtime'))
$graphvizRuntime = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'graphviz'))
$licenses = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'licenses'))
$allowedGeneratedPaths = $pythonRuntime, $graphvizRuntime, $licenses
$vcpkgRoot = Join-Path $repositoryRoot 'runtime-downloads\vcpkg'
$vcpkgComplianceRoot = Join-Path $repositoryRoot 'runtime-downloads\vcpkg-compliance'
$graphvizMsvcPatch = Join-Path $PSScriptRoot 'graphviz-msvc-stdalign.diff'

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
        if (-not $target.PSIsContainer) {
            throw "Refusing to remove generated path that is not a directory: $normalizedPath"
        }
        if (($target.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Refusing to remove generated directory that is a reparse point: $normalizedPath"
        }
        Remove-Item -LiteralPath $normalizedPath -Recurse -Force
    }
}

function Get-VerifiedDownload([string]$Uri, [string]$Sha256, [string]$Destination) {
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $Destination
    $actual = Get-Sha256 $Destination
    if ($actual -ne $Sha256) {
        throw "Checksum mismatch for $Uri. Expected $Sha256; got $actual."
    }
}

function Write-TextFile([string]$Path, [string]$Content) {
    New-Directory (Split-Path -Parent $Path)
    [IO.File]::WriteAllText($Path, $Content, [Text.UTF8Encoding]::new($false))
}

function Copy-DirectoryContents([string]$Source, [string]$Destination) {
    if (-not (Test-Path -LiteralPath $Source)) {
        return
    }
    New-Directory $Destination
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
}

$temporary = Join-Path ([IO.Path]::GetTempPath()) ("python2uml-runtime-" + [guid]::NewGuid())
$environmentNames = 'PATH', 'EXTENSION_GRAPHVIZ_DOT', 'PYTHONNOUSERSITE', 'PYTHONUNBUFFERED'
$savedEnvironment = @{}
foreach ($name in $environmentNames) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
New-Directory $temporary
Push-Location $repositoryRoot
try {
    Remove-GeneratedDirectory $pythonRuntime
    Remove-GeneratedDirectory $graphvizRuntime
    Remove-GeneratedDirectory $licenses
    if (Test-Path -LiteralPath $vcpkgRoot) { Remove-Item -LiteralPath $vcpkgRoot -Recurse -Force }
    if (Test-Path -LiteralPath $vcpkgComplianceRoot) { Remove-Item -LiteralPath $vcpkgComplianceRoot -Recurse -Force }

    New-Directory $pythonRuntime
    New-Directory $graphvizRuntime
    New-Directory (Join-Path $licenses 'python')
    New-Directory $vcpkgComplianceRoot

    $pythonArchive = Join-Path $temporary 'python.zip'
    $requirements = Join-Path $temporary 'requirements.txt'
    $graphvizCompliancePortRoot = Join-Path $vcpkgComplianceRoot 'ports\graphviz'
    $graphvizComplianceDownloadsRoot = Join-Path $vcpkgComplianceRoot 'downloads'
    $graphvizComplianceCommitPath = Join-Path $vcpkgComplianceRoot 'commit.txt'
    $graphvizComplianceProvenancePath = Join-Path $vcpkgComplianceRoot 'provenance.json'
    $graphvizManifestPath = Join-Path $licenses 'graphviz\shipped-dlls.sha256'
    $graphvizLicenseRoot = Join-Path $licenses 'graphviz'

    Get-VerifiedDownload $pythonUrl $pythonSha256 $pythonArchive
    Expand-Archive -LiteralPath $pythonArchive -DestinationPath $pythonRuntime

    $pth = Join-Path $pythonRuntime 'python312._pth'
    $pthContent = (Get-Content -LiteralPath $pth -Raw).Replace('#import site', "Lib/site-packages`r`nimport site")
    Set-Content -LiteralPath $pth -Value $pthContent -NoNewline -Encoding ascii

    $ErrorActionPreference = 'Continue'
    & git clone $vcpkgRepositoryUrl $vcpkgRoot
    $gitCloneExitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($gitCloneExitCode -ne 0) { throw 'git clone for vcpkg failed.' }
    $ErrorActionPreference = 'Continue'
    & git -C $vcpkgRoot checkout $vcpkgCommit
    $gitCheckoutExitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($gitCheckoutExitCode -ne 0) { throw 'git checkout for the pinned vcpkg commit failed.' }
    if (-not (Test-Path -LiteralPath $graphvizMsvcPatch -PathType Leaf)) { throw "Graphviz MSVC compatibility patch was not found: $graphvizMsvcPatch" }
    $graphvizPortRoot = Join-Path $vcpkgRoot 'ports\graphviz'
    Copy-Item -LiteralPath $graphvizMsvcPatch -Destination (Join-Path $graphvizPortRoot 'msvc-stdalign.diff') -Force
    $graphvizPortfile = Join-Path $graphvizPortRoot 'portfile.cmake'
    $graphvizPortfileContent = Get-Content -LiteralPath $graphvizPortfile -Raw
    if ($graphvizPortfileContent -notmatch '(?m)^        version\.diff\r?$') { throw "Pinned Graphviz portfile did not contain the expected patch anchor: $graphvizPortfile" }
    [IO.File]::WriteAllText($graphvizPortfile, ($graphvizPortfileContent -replace '(?m)^(        version\.diff)\r?$', "`$1`r`n        msvc-stdalign.diff"), [Text.UTF8Encoding]::new($false))
    & (Join-Path $vcpkgRoot 'bootstrap-vcpkg.bat')
    if ($LASTEXITCODE -ne 0) { throw 'vcpkg bootstrap failed.' }

    & (Join-Path $vcpkgRoot 'vcpkg.exe') install 'graphviz[tools]:x64-windows' --triplet x64-windows --disable-metrics
    if ($LASTEXITCODE -ne 0) { throw 'vcpkg Graphviz build failed.' }

    $installedStatus = Join-Path $vcpkgRoot 'installed\vcpkg\status'
    if (-not (Test-Path -LiteralPath $installedStatus -PathType Leaf)) { throw 'vcpkg installed-package status was not created.' }
    Copy-Item -LiteralPath $installedStatus -Destination (Join-Path $vcpkgComplianceRoot 'installed\vcpkg\status') -Force
    Get-Content -LiteralPath $installedStatus | Where-Object { $_ -like 'Package: *' } | ForEach-Object { $_.Substring(9) } | Sort-Object -Unique | ForEach-Object {
        $port = Join-Path $vcpkgRoot (Join-Path 'ports' $_)
        if (-not (Test-Path -LiteralPath $port -PathType Container)) { throw "Installed package port was not found: $_" }
        Copy-DirectoryContents $port (Join-Path $vcpkgComplianceRoot (Join-Path 'ports' $_))
    }
    if (Test-Path -LiteralPath (Join-Path $vcpkgRoot 'downloads')) {
        Copy-DirectoryContents (Join-Path $vcpkgRoot 'downloads') $graphvizComplianceDownloadsRoot
    }
    Write-TextFile $graphvizComplianceCommitPath $vcpkgCommit
    $provenance = [ordered]@{
        vcpkgCommit      = $vcpkgCommit
        graphvizFeature  = 'tools'
        triplet          = 'x64-windows'
        graphvizPortRoot = 'ports/graphviz'
        downloadsRoot    = 'downloads'
        runtimeManifest  = 'licenses/graphviz/shipped-dlls.sha256'
    }
    Write-TextFile $graphvizComplianceProvenancePath ($provenance | ConvertTo-Json -Depth 5)

    $installedRoot = Join-Path $vcpkgRoot 'installed\x64-windows'
    if (-not (Test-Path -LiteralPath $installedRoot)) { throw 'The vcpkg x64-windows install tree was not created.' }

    $dotCandidates = @(Get-ChildItem -LiteralPath $installedRoot -Filter dot.exe -File -Recurse)
    if ($dotCandidates.Count -eq 0) { throw 'dot.exe was not found in the vcpkg Graphviz install tree.' }

    $dot = $dotCandidates | Select-Object -First 1
    New-Directory (Join-Path $graphvizRuntime 'bin')
    Copy-Item -LiteralPath $dot.FullName -Destination (Join-Path $graphvizRuntime 'bin\dot.exe') -Force
    Copy-DirectoryContents $dot.Directory.FullName (Join-Path $graphvizRuntime 'bin')
    foreach ($relative in @('bin', 'lib', 'share')) {
        $source = Join-Path $installedRoot $relative
        if (Test-Path -LiteralPath $source) {
            Copy-DirectoryContents $source (Join-Path $graphvizRuntime $relative)
        }
    }

    $vcRuntimePatterns = @('^vcruntime', '^msvcp', '^concrt', '^ucrtbase')
    Get-ChildItem -LiteralPath (Join-Path $graphvizRuntime 'bin') -File | Where-Object {
        $name = $_.Name.ToLowerInvariant()
        foreach ($pattern in $vcRuntimePatterns) {
            if ($name -match $pattern) {
                return $true
            }
        }
        return $false
    } | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Force
    }

    New-Directory $graphvizLicenseRoot
    $licenseDestination = Join-Path $graphvizLicenseRoot 'LICENSE'
    $licenseCandidates = @(
        (Join-Path $vcpkgRoot 'ports\graphviz\LICENSE'),
        (Join-Path $vcpkgRoot 'ports\graphviz\copyright'),
        (Join-Path $installedRoot 'share\graphviz\copyright'),
        (Join-Path $installedRoot 'share\graphviz\LICENSE'),
        (Join-Path $installedRoot 'share\graphviz\COPYING')
    )
    $copiedLicense = $false
    foreach ($candidate in $licenseCandidates) {
        if (Test-Path -LiteralPath $candidate) {
            Copy-Item -LiteralPath $candidate -Destination $licenseDestination -Force
            $copiedLicense = $true
            break
        }
    }
    if (-not $copiedLicense) {
        Write-TextFile $licenseDestination 'Bundled Graphviz runtime from the vcpkg graphviz port and the pinned vcpkg commit.'
    }

    $shareRoot = Join-Path $installedRoot 'share'
    if (Test-Path -LiteralPath $shareRoot) {
        $licenseFiles = Get-ChildItem -LiteralPath $shareRoot -Recurse -File | Where-Object {
            $_.Name -in @('copyright', 'LICENSE', 'NOTICE', 'COPYING', 'README') -or $_.Name -like '*.spdx.json'
        }
        foreach ($file in $licenseFiles) {
            $relativePath = $file.FullName.Substring($shareRoot.Length + 1)
            $destination = Join-Path $graphvizLicenseRoot ("share\" + $relativePath)
            New-Directory (Split-Path -Parent $destination)
            Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
        }
    }

    New-Directory (Join-Path $graphvizLicenseRoot 'vcpkg')
    Copy-DirectoryContents $vcpkgComplianceRoot (Join-Path $graphvizLicenseRoot 'vcpkg')

    $manifestLines = New-Object System.Collections.Generic.List[string]
    Get-ChildItem -LiteralPath $graphvizRuntime -File -Recurse | Sort-Object FullName | ForEach-Object {
        $relativePath = $_.FullName.Substring($graphvizRuntime.Length + 1).Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $manifestLines.Add("$hash  $relativePath")
    }
    Write-TextFile $graphvizManifestPath ($manifestLines -join [Environment]::NewLine)

    Copy-Item -LiteralPath (Join-Path $pythonRuntime 'LICENSE.txt') -Destination (Join-Path $licenses 'python\LICENSE.txt') -Force

    & uv export --locked --no-dev --no-emit-project --output-file $requirements
    if ($LASTEXITCODE -ne 0) { throw 'uv export failed.' }
    $sitePackages = Join-Path $pythonRuntime 'Lib\site-packages'
    & uv pip install --python $BuildPython --only-binary=:all: --requirement $requirements --target $sitePackages
    if ($LASTEXITCODE -ne 0) { throw 'Production dependency installation failed.' }
    & uv pip install --python $BuildPython --no-deps --no-build-isolation --target $sitePackages $repositoryRoot
    if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed.' }
    $targetLock = Join-Path $sitePackages '.lock'
    if (Test-Path -LiteralPath $targetLock) { Remove-Item -LiteralPath $targetLock -Force }

    $bundledPython = Join-Path $pythonRuntime 'python.exe'
    $bundledDot = Join-Path $graphvizRuntime 'bin\dot.exe'
    [Environment]::SetEnvironmentVariable('EXTENSION_GRAPHVIZ_DOT', $bundledDot, 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONNOUSERSITE', '1', 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONUNBUFFERED', '1', 'Process')
    [Environment]::SetEnvironmentVariable('PATH', "$(Split-Path -Parent $bundledDot)$([IO.Path]::PathSeparator)$env:PATH", 'Process')

    & $bundledPython -c 'import python2uml, graphviz, tree_sitter'
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Python import smoke test failed.' }
    & $bundledDot -c
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Graphviz plugin configuration failed.' }
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
