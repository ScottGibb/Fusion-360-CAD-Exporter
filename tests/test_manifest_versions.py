"""Verify shared releases update both Fusion tools without changing metadata."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class ManifestVersionTests(unittest.TestCase):
    def setUp(self):
        script = (
            Path(__file__).resolve().parents[1] / ".github/scripts/update-manifest.py"
        )
        spec = importlib.util.spec_from_file_location("update_manifest", script)
        self.updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.updater)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.version = self.root / "version.txt"
        self.version.write_text("2.3.4\n")
        self.manifests = []
        for tool, kind in (
            ("Export3DModelRelease", "addin"),
            ("ExportDrawingPDF", "script"),
        ):
            path = self.root / tool / f"{tool}.manifest"
            path.parent.mkdir()
            path.write_text(json.dumps({"type": kind, "id": tool, "version": "1.0.0"}))
            self.manifests.append(path)

    def test_default_paths_update_both_tools_outside_repository_cwd(self):
        with (
            patch.object(self.updater, "REPO_ROOT", self.root),
            patch.dict(self.updater.os.environ, {}, clear=True),
        ):
            self.updater.main()
        for path, kind in zip(self.manifests, ("addin", "script")):
            self.assertEqual(
                json.loads(path.read_text()),
                {
                    "version": "2.3.4",
                    "type": kind,
                    "id": path.stem,
                },
            )

    def test_missing_second_manifest_does_not_modify_first(self):
        previous = self.manifests[0].read_bytes()
        self.manifests[1].unlink()
        with self.assertRaises(FileNotFoundError):
            self.updater.update_manifests(self.version, self.manifests)
        self.assertEqual(self.manifests[0].read_bytes(), previous)

    def test_empty_version_does_not_modify_manifests(self):
        self.version.write_text("\n")
        previous = [path.read_bytes() for path in self.manifests]
        with self.assertRaisesRegex(ValueError, "empty"):
            self.updater.update_manifests(self.version, self.manifests)
        self.assertEqual([path.read_bytes() for path in self.manifests], previous)

    def test_custom_manifest_override_updates_only_requested_tool(self):
        with patch.dict(
            self.updater.os.environ,
            {
                "VERSION_FILE_PATH": str(self.version),
                "MANIFEST_FILE_PATH": str(self.manifests[1]),
            },
            clear=True,
        ):
            self.updater.main()
        self.assertEqual(json.loads(self.manifests[0].read_text())["version"], "1.0.0")
        self.assertEqual(json.loads(self.manifests[1].read_text())["version"], "2.3.4")


if __name__ == "__main__":
    unittest.main()
