# Bundled Windows Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Windows x64 VSIX containing pinned Python and Graphviz runtimes so UML generation needs no system Python, Graphviz installation, network access, venv, or user-side package installation.

**Architecture:** Preserve the one-shot `python -m python2uml` CLI and `graphviz.Digraph.render()`. TypeScript resolves both bundled executables from the extension URI, supplies a child-only environment with bundled Graphviz first on `PATH`, and Python verifies the configured and resolved `dot.exe` are identical. One PowerShell script assembles and smoke-tests both generated runtimes locally and in Windows CI.

**Tech Stack:** TypeScript, VS Code API, Node `execFile`, CPython 3.12.10 embeddable x64, Python `graphviz`, Graphviz 15.0.0 x64, PowerShell, uv, GitHub Actions, VSCE.

## Global Constraints

- Support only `win32-x64`; other extension hosts fail before launch.
- Pin CPython 3.12.10 and Graphviz 15.0.0 with exact SHA-256 verification.
- Keep one-shot CLI execution and `Digraph.render()`.
- Never fall back to system Python or Graphviz.
- Never create a venv, invoke pip, or download files on an end user's machine.
- Local extension development uses the generated production runtime.
- Do not commit `python-runtime/`, `graphviz/`, `licenses/`, runtime downloads, or VSIX files.
- Preserve unrelated dirty and untracked files.
- Use `.venv\Scripts\python.exe` for local Python commands; Black line length is 200.

---

### Task 1: Require the bundled Graphviz executable in Python

**Files:**
- Modify: `src/python2uml/renderers/graphviz_renderer.py:5-50`
- Modify: `tests/python/test_renderers.py:1-40`

**Interfaces:**
- Consumes: `EXTENSION_GRAPHVIZ_DOT` and child `PATH`.
- Produces: `get_dot_executable() -> Path`, called before `Digraph.render()`.

- [ ] **Step 1: Write failing resolver tests**

Add to `tests/python/test_renderers.py`:

```python
from pathlib import Path
from unittest.mock import patch

from python2uml.renderers.graphviz_renderer import GraphvizRenderer, get_dot_executable


def test_graphviz_requires_bundled_dot(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("EXTENSION_GRAPHVIZ_DOT", raising=False)
    with pytest.raises(RuntimeError, match="was not supplied"):
        get_dot_executable()

    monkeypatch.setenv("EXTENSION_GRAPHVIZ_DOT", "dot.exe")
    with pytest.raises(RuntimeError, match="absolute"):
        get_dot_executable()

    missing = tmp_path / "graphviz" / "bin" / "dot.exe"
    monkeypatch.setenv("EXTENSION_GRAPHVIZ_DOT", str(missing))
    with pytest.raises(RuntimeError, match="was not found"):
        get_dot_executable()


def test_graphviz_requires_path_to_resolve_the_configured_dot(monkeypatch, tmp_path: Path):
    configured = tmp_path / "graphviz" / "bin" / "dot.exe"
    configured.parent.mkdir(parents=True)
    configured.write_bytes(b"")
    other = tmp_path / "system" / "dot.exe"
    other.parent.mkdir()
    other.write_bytes(b"")
    monkeypatch.setenv("EXTENSION_GRAPHVIZ_DOT", str(configured))

    with patch("python2uml.renderers.graphviz_renderer.shutil.which", return_value=str(other)), pytest.raises(RuntimeError, match="does not match"):
        get_dot_executable()
    with patch("python2uml.renderers.graphviz_renderer.shutil.which", return_value=str(configured)):
        assert get_dot_executable() == configured.resolve()
```

Replace the old test expecting a system Graphviz installation message.

- [ ] **Step 2: Verify the tests fail**

Run:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests\python\test_renderers.py -v
```

Expected: collection fails because `get_dot_executable` is missing.

- [ ] **Step 3: Implement the resolver**

Add `import os` and this function to `graphviz_renderer.py`:

```python
def get_dot_executable() -> Path:
    configured = os.environ.get("EXTENSION_GRAPHVIZ_DOT")
    if not configured:
        raise RuntimeError("Bundled Graphviz path was not supplied by the extension.")
    dot_path = Path(configured)
    if not dot_path.is_absolute():
        raise RuntimeError(f"Bundled Graphviz path must be absolute: {dot_path}")
    if not dot_path.is_file():
        raise RuntimeError(f"Bundled Graphviz executable was not found: {dot_path}")
    resolved = dot_path.resolve()
    discovered = shutil.which("dot")
    if discovered is None or Path(discovered).resolve() != resolved:
        raise RuntimeError(f"Graphviz on PATH does not match bundled executable: {resolved}")
    return resolved
```

Call `get_dot_executable()` at the start of `render()`, delete `_ensure_dot_available()`, and patch `get_dot_executable` in existing renderer unit tests.

- [ ] **Step 4: Format and test**

```powershell
& .\.venv\Scripts\python.exe -m black src\python2uml\renderers\graphviz_renderer.py tests\python\test_renderers.py
& .\.venv\Scripts\python.exe -m pytest tests\python\test_renderers.py -v
```

Expected: all renderer tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/python2uml/renderers/graphviz_renderer.py tests/python/test_renderers.py
git commit -m "feat: require bundled Graphviz executable"
```

---

### Task 2: Launch only the bundled runtime from TypeScript

**Files:**
- Modify: `src/pythonRunner.ts:1-183`
- Modify: `src/umlGenerator.ts:1-87`
- Modify: `tests/extension/extension.test.ts:7-199`

**Interfaces:**
- Produces: `BundledRuntime`, `resolveBundledRuntime(extensionUri, platform?, architecture?)`, and `runScript(runtime, args, run?)`.
- Consumes: `ExtensionContext.extensionUri`; one runtime value is reused for preview and save rerenders.

- [ ] **Step 1: Replace the venv test with failing bundled-runtime tests**

Import `resolveBundledRuntime` instead of `setupVenv`, then add:

```typescript
test("resolves an isolated bundled Windows runtime", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "python2uml runtime "));
  const extension = vscode.Uri.file(root);
  const python = path.join(root, "python-runtime", "python.exe");
  const dot = path.join(root, "graphviz", "bin", "dot.exe");
  fs.mkdirSync(path.dirname(python), { recursive: true });
  fs.mkdirSync(path.dirname(dot), { recursive: true });
  fs.writeFileSync(python, "");
  fs.writeFileSync(dot, "");
  const parentPath = process.env.PATH;
  try {
    const runtime = resolveBundledRuntime(extension, "win32", "x64");
    assert.strictEqual(runtime.pythonExec, python);
    assert.strictEqual(runtime.dotExec, dot);
    assert.strictEqual(runtime.env.EXTENSION_GRAPHVIZ_DOT, dot);
    assert.strictEqual(runtime.env.PYTHONNOUSERSITE, "1");
    assert.strictEqual(runtime.env.PYTHONUNBUFFERED, "1");
    assert.strictEqual(runtime.env.PATH?.split(path.delimiter)[0], path.dirname(dot));
    assert.strictEqual(process.env.PATH, parentPath);
  } finally {
    fs.rmSync(root, { recursive: true });
  }
});

test("rejects unsupported hosts and missing runtimes", () => {
  const extension = vscode.Uri.file(path.join(os.tmpdir(), "missing-runtime"));
  assert.throws(() => resolveBundledRuntime(extension, "linux", "x64"), /only Windows x64.*linux-x64/);
  assert.throws(() => resolveBundledRuntime(extension, "win32", "arm64"), /only Windows x64.*win32-arm64/);
  assert.throws(() => resolveBundledRuntime(extension, "win32", "x64"), /python\.exe/);
});
```

Update the invocation test so its fake runner accepts a third options argument and asserts `{ env, windowsHide: true }`.

- [ ] **Step 2: Verify TypeScript compilation fails**

Run `npm run compile`.

Expected: missing bundled-runtime exports and changed runner signature errors.

- [ ] **Step 3: Remove venv setup and add runtime resolution**

Delete `projectMarker`, `setupVenv`, marker hashing, `venv`, `ensurepip`, and `pip` calls. Add:

```typescript
type ProcessOptions = { env: NodeJS.ProcessEnv; windowsHide: boolean };
type ProcessRunner = (executable: string, args: string[], options: ProcessOptions) => Promise<ProcessResult>;

export interface BundledRuntime {
  pythonExec: string;
  dotExec: string;
  env: NodeJS.ProcessEnv;
}

function requireFile(filePath: string, label: string): void {
  try {
    if (fs.statSync(filePath).isFile()) return;
  } catch {}
  throw new Error(`${label} was not found: ${filePath}`);
}

export function resolveBundledRuntime(
  extensionUri: Uri,
  platform = process.platform,
  architecture = process.arch,
): BundledRuntime {
  if (platform !== "win32" || architecture !== "x64") {
    throw new Error(`Python2UML currently supports only Windows x64; detected ${platform}-${architecture}`);
  }
  const pythonExec = Uri.joinPath(extensionUri, "python-runtime", "python.exe").fsPath;
  const dotExec = Uri.joinPath(extensionUri, "graphviz", "bin", "dot.exe").fsPath;
  requireFile(pythonExec, "Bundled Python executable");
  requireFile(dotExec, "Bundled Graphviz executable");
  const graphvizBin = path.dirname(dotExec);
  return {
    pythonExec,
    dotExec,
    env: {
      ...process.env,
      PATH: `${graphvizBin}${path.delimiter}${process.env.PATH ?? ""}`,
      EXTENSION_GRAPHVIZ_DOT: dotExec,
      PYTHONNOUSERSITE: "1",
      PYTHONUNBUFFERED: "1",
    },
  };
}
```

Change `runScript` to accept `BundledRuntime` and call:

```typescript
const { stdout } = await run(runtime.pythonExec, ["-m", "python2uml", ...args], {
  env: runtime.env,
  windowsHide: true,
});
```

Format rejected process errors with available executable path, platform/architecture, exit code, and stderr.

- [ ] **Step 4: Route generation through the runtime**

In `umlGenerator.ts`, resolve once with:

```typescript
const runtime = resolveBundledRuntime(context.extensionUri);
```

Pass `runtime` to both `runScript` calls and remove runtime use of storage URIs.

- [ ] **Step 5: Verify extension code**

```powershell
npm run compile
npm run lint
npm test
```

Expected: all commands pass.

- [ ] **Step 6: Commit**

```powershell
git add src/pythonRunner.ts src/umlGenerator.ts tests/extension/extension.test.ts
git commit -m "feat: launch bundled Python runtime"
```

---

### Task 3: Assemble pinned Python and Graphviz runtimes

**Files:**
- Create: `scripts/build-windows-runtime.ps1`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `uv.lock`
- Modify: `.gitignore`
- Modify: `.vscodeignore`
- Modify: `package.json`

**Interfaces:**
- Produces ignored `python-runtime/`, `graphviz/`, and `licenses/` directories.
- Consumes build-time CPython 3.12 x64, `uv`, `pyproject.toml`, and `uv.lock`.

- [ ] **Step 1: Create and validate the dependency lock**

```powershell
uv lock --python 3.12
uv lock --check
```

Expected: `uv.lock` is created and valid.

- [ ] **Step 2: Define generated-file and packaging policy**

Append to `.gitignore`:

```gitignore
/python-runtime/
/graphviz/
/licenses/
/runtime-downloads/
```

Do not exclude those paths in `.vscodeignore`; add these final negations so future broad rules cannot remove packaged runtimes:

```gitignore
!python-runtime/**
!graphviz/**
!licenses/**
!THIRD_PARTY_NOTICES.md
```

Add to `package.json` scripts:

```json
"build:runtime:win32-x64": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows-runtime.ps1"
```

- [ ] **Step 3: Add third-party notices**

Create `THIRD_PARTY_NOTICES.md` naming CPython 3.12.10 (PSF License Version 2, `licenses/python/LICENSE.txt`) and Graphviz 15.0.0 (Eclipse Public License 2.0, `licenses/graphviz/LICENSE`). Include these upstream release URLs and state that only `python312._pth` is configured:

```text
https://www.python.org/downloads/release/python-31210/
https://gitlab.com/graphviz/graphviz/-/releases/15.0.0
```

- [ ] **Step 4: Write the PowerShell assembly script**

Create `scripts/build-windows-runtime.ps1`. It must use these exact constants:

```powershell
$pythonUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
$pythonSha256 = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'
$graphvizUrl = 'https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/15.0.0/windows_10_cmake_Release_Graphviz-15.0.0-win64.zip'
$graphvizSha256 = '778217b6e9f588310b21907be0525e8c3c6707b0ce0ad2be574a440fcc97cd29'
$graphvizLicenseUrl = 'https://gitlab.com/graphviz/graphviz/-/raw/15.0.0/LICENSE'
$graphvizLicenseSha256 = '0becf16567beb77fa252b7664631dd177c8f9a1889e48995b45379c7130e5303'
```

After the constants, implement the complete assembly body:

```powershell
[CmdletBinding()]
param([string]$BuildPython = (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'))
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
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

    Get-ChildItem -LiteralPath $sitePackages -Directory -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $sitePackages -File -Recurse -Include *.pyc, *.pyo | Remove-Item -Force

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
```

- [ ] **Step 5: Run the assembler and verify its outputs**

```powershell
npm run build:runtime:win32-x64
& .\python-runtime\python.exe -c "import python2uml, graphviz, tree_sitter"
& .\graphviz\bin\dot.exe -V
```

Expected: all commands exit 0 and the script's real CLI SVG smoke test passes.

- [ ] **Step 6: Verify Git and VSIX inclusion policy**

```powershell
git check-ignore python-runtime/python.exe graphviz/bin/dot.exe licenses/python/LICENSE.txt
npx vsce ls --target win32-x64 | Select-String 'python-runtime/python.exe|graphviz/bin/dot.exe|licenses/python/LICENSE.txt|THIRD_PARTY_NOTICES.md'
```

Expected: Git ignores generated files and VSCE lists all four package entries.

- [ ] **Step 7: Commit**

```powershell
git add .gitignore .vscodeignore package.json package-lock.json uv.lock scripts/build-windows-runtime.ps1 THIRD_PARTY_NOTICES.md
git commit -m "build: assemble pinned Windows runtime"
```

---

### Task 4: Build and publish a Windows x64 VSIX

**Files:**
- Modify: `.github/workflows/build.yml`
- Modify: `.github/workflows/release.yml`
- Modify: `README.md:7-34`

**Interfaces:**
- Consumes: `npm run build:runtime:win32-x64`.
- Produces: inspected `win32-x64` VSIX artifacts and accurate user/developer documentation.

- [ ] **Step 1: Convert the artifact workflow to Windows**

Change `build.yml` to `runs-on: windows-latest`, then set up Node 24, CPython 3.12 x64, and uv. Use these build commands:

```yaml
- run: npm ci
- run: uv sync --extra dev --frozen
- run: uv run --frozen --extra dev python -m black --check src/python2uml tests/python
- run: uv run --frozen --extra dev python -m pytest -v
- run: npm run compile
- run: npm run lint
- run: npm test
- run: npm run build:runtime:win32-x64 -- -BuildPython "${{ env.pythonLocation }}\python.exe"
- run: npm run package -- --target win32-x64 --out python2uml-win32-x64-${{ github.sha }}.vsix
```

Expand the VSIX under `$env:RUNNER_TEMP` and assert these exact entries exist:

```text
extension/out/src/extension.js
extension/python-runtime/python.exe
extension/python-runtime/Lib/site-packages/python2uml/__init__.py
extension/graphviz/bin/dot.exe
extension/graphviz/lib
extension/graphviz/share
extension/licenses/python/LICENSE.txt
extension/licenses/graphviz/LICENSE
extension/THIRD_PARTY_NOTICES.md
```

Fail if entries contain `.venv`, `.git`, `__pycache__`, `tests`, `pytest`, or `black`, then upload the inspected VSIX.

- [ ] **Step 2: Convert release publication to Windows**

Apply the same runtime setup, verification, assembly, target, and inspection to `release.yml`. Package `python2uml-win32-x64-${{ github.event.release.tag_name }}.vsix` and pass that exact file to `vsce publish --packagePath`.

Keep two explicit jobs; a reusable workflow is deferred until duplication becomes costly.

- [ ] **Step 3: Update README requirements**

Document that Marketplace use requires a Windows x64 extension host and bundles Python/Graphviz. State that WSL, remote hosts, ARM64, Linux, and macOS are unsupported. Retain Python 3.11+ and Graphviz only for source CLI development. Add `npm run build:runtime:win32-x64` before Extension Development Host testing. Remove all venv/pip setup claims for the extension.

- [ ] **Step 4: Package and inspect locally**

```powershell
npm run package -- --target win32-x64 --out python2uml-win32-x64-local.vsix
tar -tf python2uml-win32-x64-local.vsix | Select-String 'extension/python-runtime/python.exe|extension/graphviz/bin/dot.exe|extension/licenses/python/LICENSE.txt|extension/THIRD_PARTY_NOTICES.md'
```

Expected: packaging succeeds and all required entries are shown.

- [ ] **Step 5: Commit**

```powershell
git add .github/workflows/build.yml .github/workflows/release.yml README.md
git commit -m "ci: package self-contained Windows VSIX"
```

---

### Task 5: Complete migration verification

**Files:**
- Modify only files required by failures found below.

**Interfaces:**
- Consumes: all previous deliverables.
- Produces: final source, generated-runtime, and VSIX evidence.

- [ ] **Step 1: Confirm user-side setup is gone**

```powershell
rg -n 'setupVenv|ensurepip|projectMarker|globalStorageUri|storageUri|pip.*install' src tests/extension
```

Expected: no production venv/install logic remains.

- [ ] **Step 2: Run Python verification**

```powershell
& .\.venv\Scripts\python.exe -m black --check src\python2uml tests\python
& .\.venv\Scripts\python.exe -m pytest -v
```

Expected: Black is clean and all tests pass.

- [ ] **Step 3: Run extension verification**

```powershell
npm run compile
npm run lint
npm test
```

Expected: all commands pass.

- [ ] **Step 4: Rebuild and inspect the distributable**

```powershell
npm run build:runtime:win32-x64
npm run package -- --target win32-x64 --out python2uml-win32-x64-verify.vsix
tar -tf python2uml-win32-x64-verify.vsix | Select-String 'extension/python-runtime/python.exe|extension/python-runtime/Lib/site-packages/python2uml/__init__.py|extension/graphviz/bin/dot.exe|extension/graphviz/lib/|extension/graphviz/share/|extension/licenses/python/LICENSE.txt|extension/licenses/graphviz/LICENSE|extension/THIRD_PARTY_NOTICES.md'
```

Expected: assembly and packaging succeed and every required path is present.

- [ ] **Step 5: Run repository hygiene checks**

```powershell
git diff --check
rg -n 're\.(match|search|findall|finditer|sub)|import re|from re import' src\python2uml\parsers
git status --short
```

Expected: clean whitespace, no source-language parser regex implementation, and only intended changes plus preserved unrelated user files.

- [ ] **Step 6: Commit verification corrections only if needed**

```powershell
git commit -m "fix: complete bundled runtime verification"
```

Do not create an empty commit when no correction was required.
