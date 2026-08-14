$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $repositoryRoot "services\task-service"
$environmentRoot = Join-Path $repositoryRoot ".runtime\sidecar-venv"
$environmentPython = Join-Path $environmentRoot "Scripts\python.exe"

if ($env:ML_GUI_PYTHON) {
    $bootstrapPython = $env:ML_GUI_PYTHON
} elseif (Test-Path "D:\Python\python11\python.exe") {
    $bootstrapPython = "D:\Python\python11\python.exe"
} else {
    $bootstrapPython = (Get-Command python -ErrorAction Stop).Source
}

& $bootstrapPython -c "import sys; assert sys.version_info[:2] == (3, 11), f'PythonRuntimeError: Python 3.11 is required, got {sys.version}'"
if ($LASTEXITCODE -ne 0) {
    throw "PythonRuntimeError: Python 3.11 validation failed"
}

if (-not (Test-Path $environmentPython)) {
    & $bootstrapPython -m venv $environmentRoot
    if ($LASTEXITCODE -ne 0) {
        throw "SidecarEnvironmentError: virtual environment creation failed"
    }
}

$installArguments = @("-m", "pip", "install", "--no-build-isolation")
if ($env:ML_GUI_PIP_INDEX_URL) {
    $installArguments += @("--index-url", $env:ML_GUI_PIP_INDEX_URL)
}
$installArguments += ".[packaging]"

Push-Location $serviceRoot
try {
    & $environmentPython @installArguments
    if ($LASTEXITCODE -ne 0) {
        throw "SidecarDependencyError: packaging dependencies could not be installed"
    }
} finally {
    Pop-Location
}

& $environmentPython (Join-Path $repositoryRoot "scripts\build_task_service_sidecar.py")
if ($LASTEXITCODE -ne 0) {
    throw "SidecarBuildError: PyInstaller did not produce a valid sidecar"
}
