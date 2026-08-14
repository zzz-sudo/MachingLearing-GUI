param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$TargetPath
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$signingDirectory = Join-Path $repositoryRoot ".runtime\signing"
$certificatePath = Join-Path $signingDirectory "windows-release.pfx"
$timestampUrl = if ($env:WINDOWS_TIMESTAMP_URL) { $env:WINDOWS_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }

function Write-StructuredError {
    param([string]$ErrorType, [string]$Message)
    [ordered]@{
        errorType = $ErrorType
        message = $Message
        target = $TargetPath
    } | ConvertTo-Json -Compress | ForEach-Object { [Console]::Error.WriteLine($_) }
}

try {
    if (-not $env:WINDOWS_CERTIFICATE_BASE64) {
        Write-StructuredError "WindowsCertificateMissingError" "未设置 WINDOWS_CERTIFICATE_BASE64"
        exit 1
    }
    if (-not $env:WINDOWS_CERTIFICATE_PASSWORD) {
        Write-StructuredError "WindowsCertificatePasswordMissingError" "未设置 WINDOWS_CERTIFICATE_PASSWORD"
        exit 1
    }
    if (-not (Test-Path -LiteralPath $TargetPath -PathType Leaf)) {
        Write-StructuredError "WindowsSigningTargetMissingError" "待签名文件不存在"
        exit 1
    }

    $signTool = Get-Command signtool.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
    if (-not $signTool) {
        $kitRoot = "C:\Program Files (x86)\Windows Kits\10\bin"
        $signTool = Get-ChildItem -LiteralPath $kitRoot -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1 -ExpandProperty FullName
    }
    if (-not $signTool) {
        Write-StructuredError "WindowsSignToolMissingError" "未找到 signtool.exe，请安装 Windows SDK Signing Tools"
        exit 1
    }

    New-Item -ItemType Directory -Path $signingDirectory -Force | Out-Null
    [IO.File]::WriteAllBytes($certificatePath, [Convert]::FromBase64String($env:WINDOWS_CERTIFICATE_BASE64))

    # Sign every executable selected by the Tauri bundler and apply an RFC 3161 timestamp.
    & $signTool sign /fd SHA256 /tr $timestampUrl /td SHA256 /f $certificatePath /p $env:WINDOWS_CERTIFICATE_PASSWORD $TargetPath
    if ($LASTEXITCODE -ne 0) {
        Write-StructuredError "WindowsAuthenticodeSigningError" "signtool.exe 返回退出码 $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}
catch {
    Write-StructuredError "WindowsAuthenticodeSigningError" $_.Exception.Message
    exit 1
}
finally {
    if (Test-Path -LiteralPath $certificatePath) {
        Remove-Item -LiteralPath $certificatePath -Force
    }
}
