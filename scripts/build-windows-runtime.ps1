[CmdletBinding()]
param([string]$BuildPython)

$pythonUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
$pythonSha256 = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'
$graphvizUrl = 'https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/15.0.0/windows_10_cmake_Release_Graphviz-15.0.0-win64.zip'
$graphvizSha256 = '778217b6e9f588310b21907be0525e8c3c6707b0ce0ad2be574a440fcc97cd29'
$graphvizLicenseUrl = 'https://gitlab.com/graphviz/graphviz/-/raw/15.0.0/LICENSE'
$graphvizLicenseSha256 = '0becf16567beb77fa252b7664631dd177c8f9a1889e48995b45379c7130e5303'
$graphvizLicenseArtifacts = @(
    @{ RelativePath = 'graphviz\LICENSE'; Uri = $graphvizLicenseUrl; Sha256 = $graphvizLicenseSha256 }
    @{ RelativePath = 'graphviz\dependencies\brotli.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fbrotli%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '3d180008e36922a4e8daec11c34c7af264fed5962d07924aea928c38e8663c94' }
    @{ RelativePath = 'graphviz\dependencies\bzip2.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fbzip2%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'c6dbbf828498be844a89eaa3b84adbab3199e342eb5cb2ed2f0d4ba7ec0f38a3' }
    @{ RelativePath = 'graphviz\dependencies\cairo.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fcairo%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'd4d94ac5251d63fd0c5fadb706899a39ed060f04a55ae2319de04846729a53f0' }
    @{ RelativePath = 'graphviz\dependencies\expat.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fexpat%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '122f2c27000472a201d337b9b31f7eb2b52d091b02857061a8880371612d9534' }
    @{ RelativePath = 'graphviz\dependencies\fontconfig.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Ffontconfig%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '51a51aa9823704fd90bccc616cdd17ebabb5b2b3e9cbde886ca02c7002288067' }
    @{ RelativePath = 'graphviz\dependencies\freetype.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Ffreetype%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'b73152045aafe7291796bb4bc442c35f4c3c4a8f7985ba13f0a3761945d4ce74' }
    @{ RelativePath = 'graphviz\dependencies\fribidi.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Ffribidi%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '32434afcc8666ba060e111d715bfdb6c2d5dd8a35fa4d3ab8ad67d8f850d2f2b' }
    @{ RelativePath = 'graphviz\dependencies\getopt-win32.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fgetopt-win32%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'a5681bf9b05db14d86776930017c647ad9e6e56ff6bbcfdf21e5848288dfaf1b' }
    @{ RelativePath = 'graphviz\dependencies\gettext-libintl.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fgettext-libintl%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '3fe5361f24b7c49ba12911c08f5a33f9cb18871d95d9fb881f5b8a4793e04288' }
    @{ RelativePath = 'graphviz\dependencies\glib.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fglib%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'fa6f36630bb1e0c571d34b2bbdf188d08495c9dbf58f28cac112f303fc1f58fb' }
    @{ RelativePath = 'graphviz\dependencies\gts.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fgts%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'd245807f90032872d1438d741ed21e2490e1175dc8aa3afa5ddb6c8e529b58e5' }
    @{ RelativePath = 'graphviz\dependencies\harfbuzz.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fharfbuzz%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'ba8f810f2455c2f08e2d56bb49b72f37fcf68f1f4fade38977cfd7372050ad64' }
    @{ RelativePath = 'graphviz\dependencies\libffi.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Flibffi%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '67894089811f93fca47a76f85e017da6f8582d4ba0905963c6e0f1ad6df7a195' }
    @{ RelativePath = 'graphviz\dependencies\libgd.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Flibgd%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '005f4b6b0141d1bd11d371bbf7d4f67947f85a4906b7f5465f942204cf918ba3' }
    @{ RelativePath = 'graphviz\dependencies\libiconv.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Flibiconv%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'c8de54a89486d2b719760b66031eae5c0105d37e5c87bc344561fb7e7bd323af' }
    @{ RelativePath = 'graphviz\dependencies\libjpeg-turbo.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Flibjpeg-turbo%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '60c756742db3ad1913304e8b13f0e86e22e51adb50cc0b3333c163f7e45ceec1' }
    @{ RelativePath = 'graphviz\dependencies\liblzma.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fliblzma%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '72d7ef9c98be319fd34ce88b45203b36d5936f9c49e82bf3198ffee5e0c7d87e' }
    @{ RelativePath = 'graphviz\dependencies\libpng.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Flibpng%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'dfe5a536b0e5a531f844fb9c101a3089aca60772a503893b8e15f9457e369960' }
    @{ RelativePath = 'graphviz\dependencies\libwebp.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Flibwebp%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '7806e0de568ec6ca764d6e52a3765fb81ee838ca190ad7c5263ac45be782f6eb' }
    @{ RelativePath = 'graphviz\dependencies\pango.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fpango%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'd245807f90032872d1438d741ed21e2490e1175dc8aa3afa5ddb6c8e529b58e5' }
    @{ RelativePath = 'graphviz\dependencies\pcre2.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fpcre2%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '99272c55f3dcfa07a8a7e15a5c1a33096e4727de74241d65fa049fccfdd59507' }
    @{ RelativePath = 'graphviz\dependencies\pixman.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fpixman%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'fac9270f0987b96ff4533fca3548c633e02083cbba4a0172a3b149b2e4019793' }
    @{ RelativePath = 'graphviz\dependencies\tcl.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Ftcl%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'c0a69a2bfd757361ec7e6143973b103c90409316b49e9c88db26ad6388e79f16' }
    @{ RelativePath = 'graphviz\dependencies\tiff.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Ftiff%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '0780558a8bfba0af1160ec1ff11ade4f41c0d7deafd6ecfc796b492a788e380d' }
    @{ RelativePath = 'graphviz\dependencies\zlib.txt'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fzlib%2Fcopyright/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '845efc77857d485d91fb3e0b884aaa929368c717ae8186b66fe1ed2495753243' }
    @{ RelativePath = 'graphviz\dependencies\pcre2-LICENCE'; Uri = 'https://raw.githubusercontent.com/PCRE2Project/pcre2/pcre2-10.43/LICENCE'; Sha256 = '030087e2e8dd7c1bdd26057d25d4ded8f45bbf01ad458d68665ad04b8b0fbedf' }
    @{ RelativePath = 'graphviz\dependencies\ann-Copyright.txt'; Uri = 'https://www.cs.umd.edu/users/mount/ANN/Files/1.1.2/Copyright_1.1.2.txt'; Sha256 = '3b142f4adfdf3f2aac806978c7d52dcdec968c5f32bb22d15f338e395fd1e425' }
    @{ RelativePath = 'graphviz\dependencies\ann-LGPL-2.1.txt'; Uri = 'https://www.cs.umd.edu/users/mount/ANN/Files/1.1.2/License_1.1.2.txt'; Sha256 = '81d15b6bb9472b2eccac12b2799afa0b0ddefaca91d5dfb01bfe1ea3a2fd52cd' }
    @{ RelativePath = 'graphviz\dependencies\msvc-runtime-license.docx'; Uri = 'https://visualstudio.microsoft.com/wp-content/uploads/2021/09/Visual-C-Runtime-2015-2022-License-1.docx'; Sha256 = 'f1e3d56ceb2ad68aae0711b910375009e651ac5530fa0760f0dea6e81e54fae1' }
    @{ RelativePath = 'graphviz\internal\brewer_colors'; Uri = 'https://gitlab.com/graphviz/graphviz/-/raw/15.0.0/lib/common/brewer_colors'; Sha256 = 'a069692c03e8bcd402fbd88b2e664a7cc0f39870c05cc1d751413f8302a7d34e' }
    @{ RelativePath = 'graphviz\internal\ellipse.c'; Uri = 'https://gitlab.com/graphviz/graphviz/-/raw/15.0.0/lib/common/ellipse.c'; Sha256 = 'b17d0b7670a4e046b345ac283772f32ae483b928956e95064f82248e4fd21aa7' }
    @{ RelativePath = 'graphviz\internal\randomkit.c'; Uri = 'https://gitlab.com/graphviz/graphviz/-/raw/15.0.0/lib/neatogen/randomkit.c'; Sha256 = 'f92ca7f67b6f1a972fc5b95581772b1df8482608fbbb40e1d0cbe6e616ee1dc3' }
    @{ RelativePath = 'graphviz\internal\randomkit.h'; Uri = 'https://gitlab.com/graphviz/graphviz/-/raw/15.0.0/lib/neatogen/randomkit.h'; Sha256 = '2e014ee4903ab1c6270a5f27c678ddcb357ebd0c49635f9a7ebcdb2edb661d4e' }
    @{ RelativePath = 'graphviz\internal\rbtree-LICENSE'; Uri = 'https://gitlab.com/graphviz/graphviz/-/raw/15.0.0/lib/rbtree/LICENSE'; Sha256 = 'fcb423209a3a3909f41e629a4973eab3995ceb93136dd72485fb12ad3de29dfc' }
    @{ RelativePath = 'graphviz\spdx\cairo.json'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fcairo%2Fvcpkg.spdx.json/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '63cbfcba9b298005a7b2981293a632eb16fb4ed9b8e3bd13b179f0113fa69593' }
    @{ RelativePath = 'graphviz\spdx\fribidi.json'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Ffribidi%2Fvcpkg.spdx.json/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '0c712bb40dc022e851a81a58ac5a59ae6884b6150771947f9f4a9146947d713e' }
    @{ RelativePath = 'graphviz\spdx\getopt-win32.json'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fgetopt-win32%2Fvcpkg.spdx.json/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '712f4f9541b6e2cb5101f059691fb1212171643646f93f668f03c2a4bb197a53' }
    @{ RelativePath = 'graphviz\spdx\gettext-libintl.json'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fgettext-libintl%2Fvcpkg.spdx.json/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '4a853422dc27d75015a1af3b38c0599ca7b0747439140160b4ce1cfc8ca65649' }
    @{ RelativePath = 'graphviz\spdx\glib.json'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fglib%2Fvcpkg.spdx.json/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '578f76c81a279ea2cb5ee621d7a2ae096a6765a0c6c26a20e20ff69a532a2e68' }
    @{ RelativePath = 'graphviz\spdx\gts.json'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fgts%2Fvcpkg.spdx.json/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'f932c191189bffbef99ff64a9b11f38469f2fb1a2f1685b1ff137f69433258fe' }
    @{ RelativePath = 'graphviz\spdx\libiconv.json'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Flibiconv%2Fvcpkg.spdx.json/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = 'f60dc2a6d277a200b9582669b0c49a917a8f0470601ae3a7f70e905b521e1963' }
    @{ RelativePath = 'graphviz\spdx\pango.json'; Uri = 'https://gitlab.com/api/v4/projects/20374410/repository/files/vcpkg%2Finstalled%2Fx64-windows%2Fshare%2Fpango%2Fvcpkg.spdx.json/raw?ref=ff985525b23a1a72ddb1a89482ea12233c3cbe85'; Sha256 = '8bcbdd01e08ec31690f7f358c548af4c436432dd9705c6d6016a672aac165926' }
    @{ RelativePath = 'graphviz\sources\ann_1.1.2.zip'; Uri = 'https://www.cs.umd.edu/users/mount/ANN/Files/1.1.2/ann_1.1.2.zip'; Sha256 = '1b54b58ae697202a09d793de51ee9200fe1d5c39def78d9e8f5c0d08e48afaf5' }
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$BuildPython = if ($BuildPython) { $BuildPython } else { Join-Path $repositoryRoot '.venv\Scripts\python.exe' }
$BuildPython = [IO.Path]::GetFullPath($BuildPython)
$pythonRuntime = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'python-runtime'))
$graphvizRuntime = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'graphviz'))
$licenses = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'licenses'))
$allowedGeneratedPaths = $pythonRuntime, $graphvizRuntime, $licenses

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'Runtime assembly supports only Windows x64.'
}
if (-not (Test-Path -LiteralPath $BuildPython -PathType Leaf)) {
    throw "Build-time Python was not found: $BuildPython"
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
    New-Item -ItemType Directory -Path $pythonRuntime, $graphvizRuntime, (Join-Path $licenses 'python') | Out-Null

    $pythonArchive = Join-Path $temporary 'python.zip'
    $graphvizArchive = Join-Path $temporary 'graphviz.zip'
    $verifiedLicenses = Join-Path $temporary 'verified-licenses'
    $graphvizExtract = Join-Path $temporary 'graphviz-extracted'
    $requirements = Join-Path $temporary 'requirements.txt'
    Get-VerifiedDownload $pythonUrl $pythonSha256 $pythonArchive
    Get-VerifiedDownload $graphvizUrl $graphvizSha256 $graphvizArchive
    foreach ($artifact in $graphvizLicenseArtifacts) {
        $destination = Join-Path $verifiedLicenses $artifact.RelativePath
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Get-VerifiedDownload $artifact.Uri $artifact.Sha256 $destination
    }
    Expand-Archive -LiteralPath $pythonArchive -DestinationPath $pythonRuntime
    Expand-Archive -LiteralPath $graphvizArchive -DestinationPath $graphvizExtract

    $pth = Join-Path $pythonRuntime 'python312._pth'
    $pthContent = (Get-Content -LiteralPath $pth -Raw).Replace('#import site', "Lib/site-packages`r`nimport site")
    Set-Content -LiteralPath $pth -Value $pthContent -NoNewline -Encoding ascii

    & uv export --locked --no-dev --no-emit-project --output-file $requirements
    if ($LASTEXITCODE -ne 0) { throw 'uv export failed.' }
    $sitePackages = Join-Path $pythonRuntime 'Lib\site-packages'
    & uv pip install --python $BuildPython --only-binary=:all: --requirement $requirements --target $sitePackages
    if ($LASTEXITCODE -ne 0) { throw 'Production dependency installation failed.' }
    & uv pip install --python $BuildPython --no-deps --no-build-isolation --target $sitePackages $repositoryRoot
    if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed.' }
    $targetLock = Join-Path $sitePackages '.lock'
    if (Test-Path -LiteralPath $targetLock) { Remove-Item -LiteralPath $targetLock -Force }

    $dot = Get-ChildItem -LiteralPath $graphvizExtract -Filter dot.exe -File -Recurse | Where-Object { $_.Directory.Name -eq 'bin' } | Select-Object -First 1
    if (-not $dot) { throw 'dot.exe was not found in the Graphviz archive.' }
    Copy-Item -Path (Join-Path $dot.Directory.Parent.FullName '*') -Destination $graphvizRuntime -Recurse
    Copy-Item -LiteralPath (Join-Path $pythonRuntime 'LICENSE.txt') -Destination (Join-Path $licenses 'python\LICENSE.txt')
    foreach ($artifact in $graphvizLicenseArtifacts) {
        $source = Join-Path $verifiedLicenses $artifact.RelativePath
        $destination = Join-Path $licenses $artifact.RelativePath
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination
    }

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
