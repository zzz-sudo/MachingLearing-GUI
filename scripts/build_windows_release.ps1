$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$localUpdaterKey = Join-Path $repositoryRoot ".runtime\updater.key"

function Invoke-ReleaseStep {
    param([string]$Name, [scriptblock]$Action)
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "ReleaseStepError: $Name failed with exit code $LASTEXITCODE"
    }
}

Push-Location $repositoryRoot
try {
    Invoke-ReleaseStep "version validation" { pnpm.cmd release:check }
    Invoke-ReleaseStep "sidecar build" { pnpm.cmd desktop:sidecar }
    Invoke-ReleaseStep "license inventory" { pnpm.cmd release:licenses }

    # Use the ignored local updater key unless CI already supplied the private key content or path.
    if (-not $env:TAURI_SIGNING_PRIVATE_KEY -and -not $env:TAURI_SIGNING_PRIVATE_KEY_PATH) {
        if (-not (Test-Path -LiteralPath $localUpdaterKey -PathType Leaf)) {
            throw "UpdaterPrivateKeyMissingError: set TAURI_SIGNING_PRIVATE_KEY or restore .runtime\updater.key"
        }
        $env:TAURI_SIGNING_PRIVATE_KEY_PATH = $localUpdaterKey
    }

    Invoke-ReleaseStep "Tauri release build" {
        pnpm.cmd --filter @ml-gui/desktop tauri build --config src-tauri/tauri.release.conf.json
    }
}
finally {
    Pop-Location
}
