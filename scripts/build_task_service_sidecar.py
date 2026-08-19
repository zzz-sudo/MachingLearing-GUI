from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = ROOT / "services" / "task-service"
TARGET_BINARIES = ROOT / "apps" / "desktop" / "src-tauri" / "binaries"
BUILD_ROOT = ROOT / ".runtime" / "sidecar-build"


def rust_host_triple() -> str:
    configured = os.environ.get("TAURI_TARGET_TRIPLE")
    if configured:
        return configured
    output = subprocess.check_output(["rustc", "-vV"], cwd=ROOT, text=True)
    for line in output.splitlines():
        if line.startswith("host:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("RustTargetError: rustc host triple was not reported")


def run() -> None:
    target = rust_host_triple()
    if "windows" not in target:
        raise RuntimeError(
            f"UnsupportedSidecarTargetError: this builder requires a Windows target, got {target}"
        )

    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    TARGET_BINARIES.mkdir(parents=True, exist_ok=True)
    output_executable = BUILD_ROOT / "dist" / "task-service.exe"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "task-service",
        "--distpath",
        str(BUILD_ROOT / "dist"),
        "--workpath",
        str(BUILD_ROOT / "work"),
        "--specpath",
        str(BUILD_ROOT),
        "--paths",
        str(SERVICE_ROOT),
        "--collect-data",
        "rapidocr",
        "--collect-data",
        "pymupdf",
        "--add-data",
        f"{SERVICE_ROOT / 'app' / 'training_worker.py'}{os.pathsep}app",
        "--add-data",
        f"{SERVICE_ROOT / 'app' / 'algorithm_runners' / '__init__.py'}{os.pathsep}app/algorithm_runners",
        "--add-data",
        f"{SERVICE_ROOT / 'app' / 'algorithm_runners' / 'common.py'}{os.pathsep}app/algorithm_runners",
        "--add-data",
        f"{SERVICE_ROOT / 'app' / 'algorithm_runners' / 'supervised.py'}{os.pathsep}app/algorithm_runners",
        "--exclude-module",
        "httpx",
        "--exclude-module",
        "pytest",
        str(SERVICE_ROOT / "sidecar.py"),
    ]
    subprocess.run(command, cwd=SERVICE_ROOT, check=True)
    if not output_executable.is_file():
        raise RuntimeError(
            f"SidecarBuildError: PyInstaller output was not found at {output_executable}"
        )

    target_path = TARGET_BINARIES / f"task-service-{target}.exe"
    shutil.copy2(output_executable, target_path)
    subprocess.run([str(target_path), "--check-resources"], cwd=ROOT, check=True)
    print(f"SidecarReady: {target_path}")


if __name__ == "__main__":
    run()
