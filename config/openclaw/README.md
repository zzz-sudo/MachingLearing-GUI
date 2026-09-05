# OpenClaw 本地配置

输入格式: JSON5 网关配置和环境变量令牌。输出类型: 本地 OpenAI 兼容对话接口。

本目录只保存模板和说明。实际网关配置由 `scripts/start_openclaw.ps1` 复制到 `.runtime/openclaw` 对应目录, 令牌通过 `OPENCLAW_GATEWAY_TOKEN` 注入。仓库不保存任何真实密钥。

English comment: OpenClaw is integrated through its local gateway API. The web app never receives the gateway token.
