from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.errors import WorkspaceServiceError
from app.models import OpenClawChatRequest, OpenClawChatResponse


def _configuration(project_path: Path) -> tuple[str, str | None, str]:
    config_path = project_path / "config" / "openclaw.json"
    values: dict[str, str] = {}
    if config_path.is_file():
        try:
            values = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise WorkspaceServiceError("OpenClawConfigurationError", "无法读取 OpenClaw 配置文件", "openclaw_chat", details={"path": str(config_path), "reason": str(error)}) from error
    base_url = values.get("baseUrl") or os.environ.get("OPENCLAW_BASE_URL")
    token = values.get("token") or os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    model = values.get("model") or os.environ.get("OPENCLAW_MODEL") or "openclaw/default"
    if not base_url:
        raise WorkspaceServiceError("OpenClawNotConfiguredError", "尚未配置 OpenClaw Gateway 地址", "openclaw_chat", details={"expectedConfig": str(config_path), "environment": "OPENCLAW_BASE_URL"})
    return base_url.rstrip("/"), token, model


def chat(project_path: Path, payload: OpenClawChatRequest) -> OpenClawChatResponse:
    base_url, token, model = _configuration(project_path)
    body = json.dumps({"model": model, "messages": [message.model_dump() for message in payload.messages], "stream": False}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url}/v1/chat/completions", data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise WorkspaceServiceError("OpenClawConnectionError", "OpenClaw Gateway 请求失败", "openclaw_chat", details={"baseUrl": base_url, "reason": str(error)}) from error
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise WorkspaceServiceError("OpenClawResponseError", "OpenClaw 返回内容不符合 chat completions 格式", "openclaw_chat", details={"baseUrl": base_url}) from error
    return OpenClawChatResponse(message={"role": "assistant", "content": str(content)}, model=str(result.get("model") or model))
