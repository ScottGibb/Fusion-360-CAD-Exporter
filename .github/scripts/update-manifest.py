"""
A script to synchronize the version number in Export3DModelRelease.manifest
with the version specified in a plain text file.
"""

import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO)

# Environment variable paths with defaults
MANIFEST_FILE_PATH = os.getenv(
    "MANIFEST_FILE_PATH", "Export3DModelRelease.manifest"
)
VERSION_FILE_PATH = os.getenv("VERSION_FILE_PATH", "version.txt")


def find_current_version(version_file_path: str) -> str:
    """Extracts the version string from a text file, stripping trailing whitespace/newlines."""
    with open(version_file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def update_manifest_version(manifest_path: str, new_version: str) -> None:
    """Updates the version in the specified Fusion 360 manifest file."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    old_version = manifest_data.get("version", "unknown")
    logging.info(f"Updating manifest version from {old_version} to {new_version}")

    manifest_data["version"] = new_version

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
        f.write("\n")


def main() -> None:
    try:
        current_version = find_current_version(VERSION_FILE_PATH)
        logging.info(f"Current version from {VERSION_FILE_PATH}: {current_version}")

        update_manifest_version(MANIFEST_FILE_PATH, current_version)
        logging.info(f"Updated {MANIFEST_FILE_PATH} to version {current_version}")
        logging.info("Version update completed.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()