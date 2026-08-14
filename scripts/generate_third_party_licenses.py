"""Generate deterministic third-party license inventories for the Windows installer."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = ROOT / "apps/desktop/src-tauri/resources/licenses"
JSON_OUTPUT = OUTPUT_DIRECTORY / "THIRD_PARTY_LICENSES.json"
TEXT_OUTPUT = OUTPUT_DIRECTORY / "THIRD_PARTY_NOTICES.txt"

KNOWN_LICENSES = {
    "fastapi": "MIT",
    "pyarrow": "Apache-2.0",
    "pydantic": "MIT",
    "rapidocr": "Apache-2.0",
    "uvicorn": "BSD-3-Clause",
}


class LicenseInventoryError(RuntimeError):
    """Represent a dependency metadata collection failure."""

    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def run_json(command: list[str], cwd: Path, environment: dict[str, str] | None = None) -> Any:
    process = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode != 0:
        raise LicenseInventoryError(
            "LicenseMetadataCommandError",
            f"命令 {' '.join(command)} 执行失败: {process.stderr.strip()}",
        )
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise LicenseInventoryError(
            "LicenseMetadataJsonError",
            f"命令 {' '.join(command)} 返回了无效 JSON: {error}",
        ) from error


def collect_node_licenses() -> list[dict[str, str]]:
    command = ["pnpm.cmd" if os.name == "nt" else "pnpm", "licenses", "list", "--prod", "--json"]
    grouped = run_json(command, ROOT)
    packages: list[dict[str, str]] = []
    for license_name, entries in grouped.items():
        for entry in entries:
            for version in entry.get("versions", []):
                packages.append(
                    {
                        "name": entry["name"],
                        "version": version,
                        "license": entry.get("license") or license_name or "UNKNOWN",
                        "source": entry.get("homepage") or "",
                    }
                )
    return sorted(packages, key=lambda item: (normalize_name(item["name"]), item["version"]))


def requirement_name(requirement: str) -> str | None:
    try:
        parsed = Requirement(requirement)
    except InvalidRequirement:
        match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
        return normalize_name(match.group(1)) if match else None
    marker_environment = default_environment()
    marker_environment["extra"] = ""
    if parsed.marker is not None and not parsed.marker.evaluate(marker_environment):
        return None
    return normalize_name(parsed.name)


def metadata_license(metadata: dict[str, Any], normalized_name: str) -> str:
    expression = metadata.get("license_expression") or metadata.get("license")
    if isinstance(expression, str) and expression.strip():
        return " ".join(expression.split())
    classifiers = metadata.get("classifier") or []
    license_classifiers = [item.rsplit("::", 1)[-1].strip() for item in classifiers if item.startswith("License ::")]
    if license_classifiers:
        return " OR ".join(sorted(set(license_classifiers)))
    return KNOWN_LICENSES.get(normalized_name, "UNKNOWN")


def metadata_source(metadata: dict[str, Any]) -> str:
    project_urls = metadata.get("project_url") or []
    if isinstance(project_urls, list) and project_urls:
        preferred = next((item for item in project_urls if str(item).lower().startswith("source,")), project_urls[0])
        return str(preferred).split(",", 1)[-1].strip()
    return str(metadata.get("home_page") or "")


def collect_python_licenses(python_executable: Path) -> list[dict[str, str]]:
    report = run_json([str(python_executable), "-m", "pip", "inspect", "--local"], ROOT)
    installed = {
        normalize_name(item["metadata"]["name"]): item["metadata"]
        for item in report.get("installed", [])
        if item.get("metadata", {}).get("name")
    }
    pyproject = tomllib.loads((ROOT / "services/task-service/pyproject.toml").read_text(encoding="utf-8"))
    pending = [requirement_name(item) for item in pyproject["project"]["dependencies"]]
    selected: set[str] = set()
    while pending:
        name = pending.pop()
        if name is None or name in selected:
            continue
        metadata = installed.get(name)
        if metadata is None:
            raise LicenseInventoryError(
                "PythonDependencyMetadataMissingError",
                f"许可证环境中未安装 Python 运行时依赖 {name}",
            )
        selected.add(name)
        pending.extend(requirement_name(item) for item in metadata.get("requires_dist") or [])

    packages = []
    for name in sorted(selected):
        metadata = dict(installed[name])
        distribution_metadata = importlib.metadata.metadata(str(metadata["name"]))
        metadata["license_expression"] = distribution_metadata.get("License-Expression")
        metadata["license"] = distribution_metadata.get("License") or metadata.get("license")
        metadata["classifier"] = distribution_metadata.get_all("Classifier") or metadata.get("classifier")
        metadata["project_url"] = distribution_metadata.get_all("Project-URL") or metadata.get("project_url")
        metadata["home_page"] = distribution_metadata.get("Home-page") or metadata.get("home_page")
        packages.append(
            {
                "name": str(metadata["name"]),
                "version": str(metadata["version"]),
                "license": metadata_license(metadata, name),
                "source": metadata_source(metadata),
            }
        )
    return packages


def collect_rust_licenses() -> list[dict[str, str]]:
    environment = os.environ.copy()
    environment["NO_PROXY"] = "rsproxy.cn,github.com"
    environment["no_proxy"] = environment["NO_PROXY"]
    metadata = run_json(
        ["cargo", "metadata", "--format-version", "1", "--locked"],
        ROOT / "apps/desktop/src-tauri",
        environment,
    )
    packages = []
    for package in metadata.get("packages", []):
        if package["name"] == "machinglearing-gui":
            continue
        packages.append(
            {
                "name": package["name"],
                "version": package["version"],
                "license": package.get("license") or "UNKNOWN",
                "source": package.get("repository") or package.get("homepage") or "",
            }
        )
    return sorted(packages, key=lambda item: (normalize_name(item["name"]), item["version"]))


def review_reason(license_name: str) -> str | None:
    normalized = license_name.upper()
    if "AGPL" in normalized or "AFFERO GPL" in normalized:
        return "强网络著作权许可，分发前必须确认项目整体合规或取得商业许可"
    if license_name == "UNKNOWN":
        return "缺少明确许可证元数据，需要人工确认来源包"
    return None


def write_inventory(groups: dict[str, list[dict[str, str]]]) -> None:
    review = []
    for ecosystem, packages in groups.items():
        for package in packages:
            reason = review_reason(package["license"])
            if reason:
                review.append({"ecosystem": ecosystem, **package, "reason": reason})

    document = {
        "application": "MachingLearing GUI",
        "author": "Kuroneko",
        "purpose": "Windows 安装包包含的第三方运行时依赖许可证清单",
        "generatedFrom": "pnpm production dependencies, Python sidecar environment and Cargo.lock",
        "manualReview": review,
        "dependencies": groups,
    }
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "MachingLearing GUI 第三方许可证清单",
        "作者: Kuroneko",
        "",
        "本文件列出随 Windows 安装包分发的运行时依赖及其许可证元数据。",
        "本清单不是法律意见。标记为需要人工审查的依赖必须在正式公开分发前完成许可决策。",
        "",
    ]
    if review:
        lines.extend(["需要人工审查", ""])
        for item in review:
            lines.append(
                f"{item['ecosystem']}: {item['name']} {item['version']} | {item['license']} | {item['reason']}"
            )
        lines.append("")
    for ecosystem, packages in groups.items():
        lines.extend([ecosystem, ""])
        for package in packages:
            source = f" | {package['source']}" if package["source"] else ""
            lines.append(f"{package['name']} {package['version']} | {package['license']}{source}")
        lines.append("")
    TEXT_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 Windows 安装包第三方许可证清单")
    parser.add_argument(
        "--python",
        dest="python_executable",
        type=Path,
        default=ROOT / ".runtime/sidecar-venv/Scripts/python.exe",
        help="已经安装 sidecar 运行时依赖的 Python 解释器",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if not args.python_executable.is_file():
            raise LicenseInventoryError(
                "LicensePythonEnvironmentMissingError",
                f"许可证扫描环境不存在: {args.python_executable}",
            )
        groups = {
            "node": collect_node_licenses(),
            "python": collect_python_licenses(args.python_executable),
            "rust": collect_rust_licenses(),
        }
        write_inventory(groups)
        counts = {name: len(items) for name, items in groups.items()}
        print(json.dumps({"status": "generated", "counts": counts}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, LicenseInventoryError) as error:
        error_type = error.error_type if isinstance(error, LicenseInventoryError) else type(error).__name__
        print(
            json.dumps({"errorType": error_type, "message": str(error)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
