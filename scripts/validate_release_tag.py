from __future__ import annotations

import os
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def read_project_version(pyproject_path: Path) -> str:
    with pyproject_path.open("rb") as handle:
        payload = tomllib.load(handle)

    version = str(payload.get("project", {}).get("version") or "").strip()
    if not version:
        raise ValueError("project.version is missing in pyproject.toml")
    return version


def validate_release_tag(tag_name: str, version: str) -> str:
    normalized_tag = str(tag_name or "").strip()
    expected_tag = f"v{version}"
    if normalized_tag != expected_tag:
        raise ValueError(
            f"release tag '{normalized_tag}' must match project version '{expected_tag}'"
        )
    return normalized_tag


def main() -> int:
    tag_name = os.getenv("GITHUB_REF_NAME", "").strip()
    if not tag_name:
        raise ValueError("GITHUB_REF_NAME is required")

    version = read_project_version(PYPROJECT_PATH)
    validated_tag = validate_release_tag(tag_name, version)
    print(f"validated {validated_tag} against project version {version}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
