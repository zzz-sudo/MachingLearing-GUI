from __future__ import annotations

import os
from pathlib import Path


def resolve_data_dir() -> Path:
    configured = os.environ.get("ML_GUI_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    # English comment: Prefer repository-local runtime state so projects remain portable.
    repository_root = Path(__file__).resolve().parents[3]
    if (repository_root / "workspace" / "default").is_dir():
        return repository_root / ".runtime" / "task-service"

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "MachingLearingGUI"

    return Path.home() / ".machinglearing-gui"
