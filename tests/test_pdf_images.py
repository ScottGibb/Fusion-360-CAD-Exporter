# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["pypdfium2>=4.30,<6", "Pillow>=11,<13"]
# ///
"""Real multipage PDF rendering checks; run with uv run --script."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


class ImageTests(unittest.TestCase):
    def setUp(self):
        try:
            import pypdfium2 as pdfium
            from PIL import Image
        except ImportError:
            self.skipTest("Run with uv run --script tests/test_pdf_images.py")
        self.Image = Image
        source = (
            Path(__file__).resolve().parents[1] / "ExportDrawingPDF/pdf_to_images.py"
        )
        spec = importlib.util.spec_from_file_location("pdf_to_images", source)
        self.converter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.converter)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / "drawing with spaces.pdf"
        with pdfium.PdfDocument.new() as document:
            document.new_page(72, 144).close()
            document.new_page(144, 72).close()
            document.save(str(self.pdf))
        self.original = self.pdf.read_bytes()

    def test_all_pages_both_formats_at_requested_resolution(self):
        paths = self.converter.convert_pdf(self.pdf, "both", 144)
        self.assertEqual(len(paths), 4)
        for path in paths:
            with self.Image.open(path) as image:
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
                self.assertEqual(
                    image.size, (144, 288) if "001" in path else (288, 144)
                )
                self.assertAlmostEqual(image.info["dpi"][0], 144, delta=1)
        self.assertEqual(self.pdf.read_bytes(), self.original)

    def test_png_only_and_existing_image_protection(self):
        paths = self.converter.convert_pdf(self.pdf, "png", 72)
        self.assertEqual(len(paths), 2)
        self.assertTrue(all(path.endswith(".png") for path in paths))
        Path(paths[0]).write_bytes(b"original image")
        with self.assertRaises(FileExistsError):
            self.converter.convert_pdf(self.pdf, "png", 72)
        self.assertEqual(Path(paths[0]).read_bytes(), b"original image")
        self.converter.convert_pdf(self.pdf, "png", 72, overwrite=True)
        with self.Image.open(paths[0]) as image:
            self.assertEqual(image.size, (72, 144))

    def test_bad_pdf_creates_no_images(self):
        self.pdf.write_bytes(b"this is not a PDF")
        with self.assertRaises(Exception):
            self.converter.convert_pdf(self.pdf)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [self.pdf])


if __name__ == "__main__":
    unittest.main(verbosity=2)
