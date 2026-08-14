"""Synchronize and validate the release version used by every application layer."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

JSON_TARGETS = (
    (ROOT / "package.json", ("version",)),
    (ROOT / "apps/web/package.json", ("version",)),
    (ROOT / "apps/desktop/package.json", ("version",)),
    (ROOT / "packages/contracts/package.json", ("version",)),
    (ROOT / "apps/desktop/src-tauri/tauri.conf.json", ("version",)),
)

TOML_TARGETS = (
    (ROOT / "services/task-service/pyproject.toml", "project"),
    (ROOT / "apps/desktop/src-tauri/Cargo.toml", "package"),
)


class ReleaseVersionError(RuntimeError):
    """Represent a structured release version validation failure."""

    def __init__(self, error_type: str, message: str, details: dict[str, object] | None = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


def read_json_version(path: Path, key_path: tuple[str, ...]) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    value: object = data
    for key in key_path:
        value = value[key]  # type: ignore[index]
    return str(value)


def write_json_version(path: Path, key_path: tuple[str, ...], version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    target = data
    for key in key_path[:-1]:
        target = target[key]
    target[key_path[-1]] = version
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_toml_version(path: Path, section: str) -> tuple[str, int, list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_section = False
    section_header = f"[{section}]"
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_section = stripped == section_header
            continue
        if in_section:
            match = re.fullmatch(r'\s*version\s*=\s*"([^"]+)"\s*', stripped)
            if match:
                return match.group(1), index, lines
    raise ReleaseVersionError(
        "VersionFieldMissingError",
        f"未在 {path.relative_to(ROOT)} 的 {section_header} 中找到 version",
    )


def write_toml_version(path: Path, section: str, version: str) -> None:
    _, index, lines = find_toml_version(path, section)
    newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
    lines[index] = f'version = "{version}"{newline}'
    path.write_text("".join(lines), encoding="utf-8")


def collect_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for path, key_path in JSON_TARGETS:
        versions[str(path.relative_to(ROOT))] = read_json_version(path, key_path)
    for path, section in TOML_TARGETS:
        versions[str(path.relative_to(ROOT))] = find_toml_version(path, section)[0]
    return versions


def validate_versions(expected: str | None, tag: str | None) -> str:
    versions = collect_versions()
    distinct = sorted(set(versions.values()))
    if len(distinct) != 1:
        raise ReleaseVersionError(
            "VersionMismatchError",
            "项目版本号不一致",
            {"versions": versions},
        )
    current = distinct[0]
    if expected is not None and current != expected:
        raise ReleaseVersionError(
            "UnexpectedVersionError",
            f"当前版本 {current} 与期望版本 {expected} 不一致",
            {"versions": versions},
        )
    if tag is not None and tag.removeprefix("v") != current:
        raise ReleaseVersionError(
            "ReleaseTagMismatchError",
            f"Git 标签 {tag} 与项目版本 {current} 不一致",
            {"tag": tag, "version": current},
        )
    return current


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="同步或检查 MachingLearing GUI 的发布版本")
    parser.add_argument("version", nargs="?", help="要写入的 SemVer 版本，例如 0.2.0")
    parser.add_argument("--check", action="store_true", help="仅检查全部版本字段是否一致")
    parser.add_argument("--tag", help="同时验证发布标签，例如 v0.2.0")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.check:
            current = validate_versions(args.version, args.tag)
            print(json.dumps({"status": "ok", "version": current}, ensure_ascii=False))
            return 0
        if not args.version or not SEMVER_PATTERN.fullmatch(args.version):
            raise ReleaseVersionError(
                "InvalidSemanticVersionError",
                "必须提供有效的 SemVer 版本，例如 0.2.0 或 0.2.0-beta.1",
            )
        for path, key_path in JSON_TARGETS:
            write_json_version(path, key_path, args.version)
        for path, section in TOML_TARGETS:
            write_toml_version(path, section, args.version)
        validate_versions(args.version, args.tag)
        print(json.dumps({"status": "updated", "version": args.version}, ensure_ascii=False))
        return 0
    except (KeyError, OSError, ValueError, ReleaseVersionError) as error:
        error_type = error.error_type if isinstance(error, ReleaseVersionError) else type(error).__name__
        details = error.details if isinstance(error, ReleaseVersionError) else {}
        print(
            json.dumps(
                {"errorType": error_type, "message": str(error), "details": details},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
