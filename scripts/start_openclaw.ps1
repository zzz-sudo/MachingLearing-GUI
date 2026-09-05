# 输入: 无。输出: 本项目内运行的 OpenClaw Gateway 进程。
# 功能: 使用项目目录保存 OpenClaw 状态和配置, 供本地任务服务通过 OpenAI 兼容接口调用。
# 作者: Kuroneko
# English comment: Start the gateway with project-local state to keep this repository self-contained.

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$runtimeRoot = Join-Path $projectRoot ".runtime\openclaw"
$configPath = Join-Path $projectRoot "config\openclaw\gateway.local.json5"
$connectorPath = Join-Path $projectRoot "workspace\default\config\openclaw.json"

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $configPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $connectorPath) | Out-Null

if (-not (Test-Path $configPath)) {
  $examplePath = Join-Path $projectRoot "config\openclaw\gateway.example.json5"
  if (-not (Test-Path $examplePath)) {
    throw "缺少 OpenClaw 网关模板: $examplePath"
  }
  Copy-Item -LiteralPath $examplePath -Destination $configPath
  Write-Warning "已创建本地网关配置, 请先填写提供商密钥: $configPath"
}

if (-not (Test-Path $connectorPath)) {
  Copy-Item -LiteralPath (Join-Path $projectRoot "workspace\default\config\openclaw.example.json") -Destination $connectorPath
}

$env:OPENCLAW_CONFIG_PATH = $configPath
$env:OPENCLAW_STATE_DIR = $runtimeRoot
$env:OPENCLAW_GATEWAY_TOKEN = if ($env:OPENCLAW_GATEWAY_TOKEN) { $env:OPENCLAW_GATEWAY_TOKEN } else { "" }

openclaw gateway --port 18789
