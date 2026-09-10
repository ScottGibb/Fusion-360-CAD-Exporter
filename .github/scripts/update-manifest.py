"""Keep both Fusion tool manifests on the repository's shared release version."""

import json
import logging
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = ("Export3DModelRelease", "ExportDrawingPDF")


def find_current_version(version_file_path: Path) -> str:
    """Read the release version, rejecting an empty version file."""
    version = Path(version_file_path).read_text(encoding="utf-8").strip()
    if not version:
        raise ValueError("The release version is empty.")
    return version


def update_manifests(version_file_path: Path, manifest_paths: list[Path]) -> None:
    """Validate all inputs before updating either tool's version."""
    version = find_current_version(version_file_path)
    manifests = []
    for path in manifest_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = version
        manifests.append((path, data))
    for path, data in manifests:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        logging.info("Updated %s to version %s", path, version)


def main() -> None:
    """Update both tools by default, with the existing environment overrides."""
    version_path = Path(os.getenv("VERSION_FILE_PATH", REPO_ROOT / "version.txt"))
    override = os.getenv("MANIFEST_FILE_PATH")
    manifest_paths = (
        [Path(override)]
        if override
        else [REPO_ROOT / tool / f"{tool}.manifest" for tool in TOOLS]
    )
    update_manifests(version_path, manifest_paths)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
