from __future__ import annotations

import argparse
import json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MachingLearing GUI task service sidecar")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--check-resources", action="store_true")
    return parser


def check_resources() -> None:
    from rapidocr import RapidOCR

    RapidOCR()
    print(json.dumps({"status": "ready", "resource": "rapidocr"}), flush=True)


def main() -> None:
    arguments = build_parser().parse_args()
    if arguments.check_resources:
        check_resources()
        return

    import uvicorn
    from app.main import app

    uvicorn.run(
        app,
        host=arguments.host,
        port=arguments.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
