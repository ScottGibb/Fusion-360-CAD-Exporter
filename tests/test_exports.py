"""Regression checks for Fusion state restoration and drawing PDF failures."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(filename):
    """Import the real entry points with only the unavailable adsk host stubbed."""
    adsk = types.ModuleType("adsk")
    adsk.core = types.ModuleType("adsk.core")
    adsk.fusion = types.ModuleType("adsk.fusion")
    adsk.core.__getattr__ = lambda name: object
    adsk.fusion.__getattr__ = lambda name: object
    spec = importlib.util.spec_from_file_location(Path(filename).stem, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules, {"adsk": adsk, "adsk.core": adsk.core, "adsk.fusion": adsk.fusion}
    ):
        spec.loader.exec_module(module)
    return module


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.script = load_script("Export3DModelRelease/Export3DModelRelease.py")
        # Includes a nested component with mixed original visibility settings.
        self.components = [
            types.SimpleNamespace(
                **{
                    name: visible
                    for name, visible in (
                        ("isOriginFolderLightBulbOn", True),
                        ("isConstructionFolderLightBulbOn", False),
                        ("isSketchFolderLightBulbOn", True),
                        ("isJointsFolderLightBulbOn", True),
                        ("isJointOriginsFolderLightBulbOn", True),
                        ("isCanvasFolderLightBulbOn", True),
                    )
                }
            )
            for _ in range(3)
        ]
        self.before = [vars(component).copy() for component in self.components]
        self.analyses = types.SimpleNamespace(isLightBulbOn=True)
        self.design = types.SimpleNamespace(
            allComponents=self.components, analyses=self.analyses
        )
        self.grid = types.SimpleNamespace(isSelected=True)
        control = types.SimpleNamespace(
            listItems=Mock(count=1, item=Mock(return_value=self.grid))
        )
        self.script.adsk.core.ListControlDefinition = Mock(
            cast=Mock(return_value=control)
        )
        self.script.adsk.core.SaveImageFileOptions = Mock(
            create=Mock(side_effect=lambda _: types.SimpleNamespace())
        )
        self.camera = object()
        self.viewport = Mock(camera=self.camera)
        self.selection = object()
        self.selections = Mock(
            count=1,
            item=Mock(return_value=types.SimpleNamespace(entity=self.selection)),
        )
        self.app = Mock(activeViewport=self.viewport)
        self.app.userInterface.activeSelections = self.selections
        self.viewport.saveAsImageFileWithOptions.side_effect = self.check_capture

    def check_capture(self, options):
        for component in self.components:
            self.assertFalse(any(vars(component).values()))
        self.assertFalse(self.grid.isSelected)
        self.assertFalse(self.analyses.isLightBulbOn)
        self.selections.clear.assert_called_once()
        self.assertTrue(options.isBackgroundTransparent)
        self.assertEqual((options.width, options.height), (1920, 1080))
        return True

    def assert_restored(self):
        self.assertEqual([vars(c) for c in self.components], self.before)
        self.assertTrue(self.grid.isSelected)
        self.assertTrue(self.analyses.isLightBulbOn)
        self.assertIs(self.viewport.camera, self.camera)
        self.selections.add.assert_called_once_with(self.selection)

    def test_nested_aids_hidden_and_restored(self):
        self.script._capture_model_image(self.app, self.design, "preview.png")
        self.assert_restored()

    def test_failed_save_restores_everything(self):
        def fail(options):
            self.check_capture(options)
            return False

        self.viewport.saveAsImageFileWithOptions.side_effect = fail
        with self.assertRaisesRegex(RuntimeError, "Failed to save"):
            self.script._capture_model_image(self.app, self.design, "preview.png")
        self.assert_restored()

    def test_exception_during_save_restores_everything(self):
        self.viewport.saveAsImageFileWithOptions.side_effect = RuntimeError(
            "renderer failure"
        )
        with self.assertRaisesRegex(RuntimeError, "renderer failure"):
            self.script._capture_model_image(self.app, self.design, "preview.png")
        self.assert_restored()

    def test_failed_hide_restores_earlier_changes_without_duplicate_selection(self):
        class LockedComponent:
            @property
            def isOriginFolderLightBulbOn(self):
                return True

            @isOriginFolderLightBulbOn.setter
            def isOriginFolderLightBulbOn(self, value):
                raise RuntimeError("locked component")

        self.components.append(LockedComponent())
        with self.assertRaisesRegex(RuntimeError, "locked component"):
            self.script._capture_model_image(self.app, self.design, "preview.png")
        self.assertEqual([vars(c) for c in self.components[:-1]], self.before)
        self.assertTrue(self.grid.isSelected)
        self.selections.add.assert_not_called()
        self.viewport.saveAsImageFileWithOptions.assert_not_called()


class DrawingTests(unittest.TestCase):
    def setUp(self):
        self.script = load_script("ExportDrawingPDF/ExportDrawingPDF.py")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / "drawing with spaces.pdf"
        self.options = types.SimpleNamespace()
        self.manager = Mock()
        self.manager.createPDFExportOptions.side_effect = self.make_options
        self.document = types.SimpleNamespace(
            drawing=types.SimpleNamespace(exportManager=self.manager)
        )
        self.api = types.SimpleNamespace(
            PDFSheetsExport=types.SimpleNamespace(AllPDFSheetsExport=0)
        )

    def make_options(self, filename):
        self.options.filename = filename
        return self.options

    def test_export_all_sheets_before_replacing_previous_pdf(self):
        self.pdf.write_bytes(b"previous PDF")

        def export(options):
            self.assertEqual(self.pdf.read_bytes(), b"previous PDF")
            self.assertEqual(options.sheetsToExport, 0)
            self.assertTrue(options.useLineWeights)
            self.assertFalse(options.openPDF)
            Path(options.filename).write_bytes(b"%PDF-1.7\nnew PDF")
            return True

        self.manager.execute.side_effect = export
        self.script._export_pdf(self.document, self.pdf, self.api)
        self.assertEqual(self.pdf.read_bytes(), b"%PDF-1.7\nnew PDF")

    def test_failed_export_keeps_previous_pdf(self):
        self.pdf.write_bytes(b"previous PDF")
        self.manager.execute.return_value = False
        with self.assertRaisesRegex(RuntimeError, "export failed"):
            self.script._export_pdf(self.document, self.pdf, self.api)
        self.assertEqual(self.pdf.read_bytes(), b"previous PDF")

    def test_success_without_file_is_not_reported_as_success(self):
        self.manager.execute.return_value = True
        with self.assertRaisesRegex(RuntimeError, "did not create"):
            self.script._export_pdf(self.document, self.pdf, self.api)
        self.assertFalse(self.pdf.exists())

    def test_conversion_failure_does_not_touch_pdf(self):
        self.pdf.write_bytes(b"%PDF-1.7\nkeep me")
        with (
            patch.object(self.script, "_find_uv", return_value="/tools/uv"),
            patch.object(
                self.script.subprocess,
                "run",
                return_value=Mock(returncode=1, stderr="conversion failed"),
            ) as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "conversion failed"):
                self.script._convert_images(self.pdf, "both", False)
            self.assertIn(str(self.pdf), run.call_args.args[0])
            self.assertNotIn("--overwrite", run.call_args.args[0])
        self.assertEqual(self.pdf.read_bytes(), b"%PDF-1.7\nkeep me")


if __name__ == "__main__":
    unittest.main()
