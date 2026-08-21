from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from visualization.renderer import render_chart


def main() -> None:
    config_path = Path(sys.argv[1])
    config = json.loads(config_path.read_text(encoding="utf-8"))
    result_path = Path(config["resultPath"])
    try:
        result = render_chart(config)
    except Exception as error:
        result = {
            "status": "failed",
            "chartType": config.get("chartType", "unknown"),
            "artifacts": [],
            "warnings": [],
            "environment": {},
            "errorType": type(error).__name__,
            "errorMessage": str(error),
        }
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["status"] != "succeeded":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
