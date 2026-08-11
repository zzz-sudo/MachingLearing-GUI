from __future__ import annotations

import os
from pathlib import Path


def resolve_data_dir() -> Path:
    configured = os.environ.get("ML_GUI_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "MachingLearingGUI"

    return Path.home() / ".machinglearing-gui"

