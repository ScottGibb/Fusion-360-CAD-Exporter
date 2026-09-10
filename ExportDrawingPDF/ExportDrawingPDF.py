"""Fusion script: export all drawing sheets to PDF, then PNG and/or JPEG.

PDF export uses Fusion's drawing API. Conversion runs locally in a separate
uv-managed Python environment, without installing packages into Fusion.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import traceback

import adsk.core

TITLE = "Export Drawing PDF and Images"


def _find_uv():
    """Find uv even when Fusion was launched without the shell's PATH."""
    executable = "uv.exe" if os.name == "nt" else "uv"
    candidates = [
        os.environ.get("FUSION_EXPORT_UV"),
        shutil.which(executable),
        Path.home() / ".local" / "bin" / executable,
        Path.home() / ".cargo" / "bin" / executable,
        Path.home() / ".nix-profile" / "bin" / executable,
        Path("/opt/homebrew/bin/uv"),
        Path("/usr/local/bin/uv"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise RuntimeError(
        "PDF export succeeded, but image conversion needs uv. Install uv from "
        "https://docs.astral.sh/uv/getting-started/installation/ and run again. "
        "For a custom installation, set FUSION_EXPORT_UV to its executable path."
    )


def _export_pdf(drawing_document, pdf_path, drawing_api):
    """Validate a new PDF before replacing an earlier export."""
    manager = drawing_document.drawing.exportManager
    with tempfile.TemporaryDirectory(
        prefix=".drawing-pdf-", dir=pdf_path.parent
    ) as temp:
        temporary_pdf = Path(temp) / pdf_path.name
        options = manager.createPDFExportOptions(str(temporary_pdf))
        if not options:
            raise RuntimeError("Fusion could not create PDF export options.")
        options.sheetsToExport = drawing_api.PDFSheetsExport.AllPDFSheetsExport
        options.useLineWeights = True
        options.openPDF = False
        if not manager.execute(options):
            raise RuntimeError("Fusion reported that drawing PDF export failed.")
        if not temporary_pdf.is_file() or temporary_pdf.stat().st_size < 5:
            raise RuntimeError("Fusion did not create a PDF file.")
        with temporary_pdf.open("rb") as exported:
            if exported.read(5) != b"%PDF-":
                raise RuntimeError("Fusion's output is not a PDF file.")
        os.replace(temporary_pdf, pdf_path)


def _convert_images(pdf_path, image_format, overwrite):
    """Run the local renderer without shell interpolation or Fusion imports."""
    command = [
        _find_uv(),
        "run",
        "--script",
        str(Path(__file__).with_name("pdf_to_images.py")),
        str(pdf_path),
        "--format",
        image_format,
        "--dpi",
        "300",
    ]
    if overwrite:
        command.append("--overwrite")
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        environment.pop(name, None)
    options = {"env": environment}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=600, check=False, **options
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or "PDF image conversion failed.")
    images = json.loads(result.stdout)
    if not images or any(
        not Path(path).is_file() or not Path(path).stat().st_size for path in images
    ):
        raise RuntimeError("The converter did not produce all requested images.")
    return images


def _existing_exports(pdf_path, image_format):
    """Find only the PDF and numbered image names owned by this export."""
    extensions = (
        {".png", ".jpg"}
        if image_format == "both"
        else {".jpg" if image_format == "jpeg" else ".png"}
    )
    prefix = pdf_path.stem + "-sheet-"
    existing = [pdf_path] if pdf_path.exists() else []
    for path in pdf_path.parent.iterdir():
        if path.suffix in extensions and path.stem.startswith(prefix):
            if path.stem[len(prefix) :].isdigit():
                existing.append(path)
    return existing


def run(context):
    """Run from Fusion's Scripts tab with a drawing document active."""
    app = adsk.core.Application.get()
    ui = app.userInterface
    pdf_path = None
    pdf_saved = False
    progress = None
    try:
        try:
            import adsk.drawing as drawing_api
        except ImportError as error:
            raise RuntimeError(
                "Update Fusion to a version with the drawing PDF export API."
            ) from error
        document = drawing_api.DrawingDocument.cast(app.activeDocument)
        if not document:
            ui.messageBox(
                "Open a drawing and make its tab active, then run this script.", TITLE
            )
            return
        image_format, cancelled = ui.inputBox(
            "Image format: png, jpeg, or both.\nAll sheets are exported at 300 DPI.",
            TITLE,
            "both",
        )
        if cancelled:
            return
        image_format = image_format.strip().lower()
        if image_format == "jpg":
            image_format = "jpeg"
        if image_format not in {"png", "jpeg", "both"}:
            raise ValueError("Enter png, jpeg, or both for the image format.")
        dialog = ui.createFileDialog()
        dialog.title = "Save drawing PDF and images"
        dialog.filter = "PDF files (*.pdf)"
        dialog.filterIndex = 0
        source = document.dataFile
        name = f"{source.name}-v{source.versionNumber}" if source else document.name
        name = "".join(char if char.isalnum() or char in "-_" else "-" for char in name)
        dialog.initialFilename = f"{name}-drawing.pdf"
        if dialog.showSave() != adsk.core.DialogResults.DialogOK:
            return
        pdf_path = Path(dialog.filename).expanduser().resolve()
        if pdf_path.suffix.lower() != ".pdf":
            pdf_path = pdf_path.with_suffix(".pdf")
        existing = _existing_exports(pdf_path, image_format)
        if existing:
            answer = ui.messageBox(
                "Replace the existing PDF and matching sheet images for this name?\n"
                "Images from sheets removed since the previous export are retained.",
                TITLE,
                adsk.core.MessageBoxButtonTypes.YesNoButtonType,
            )
            if answer != adsk.core.DialogResults.DialogYes:
                return
        progress = ui.createProgressDialog()
        progress.isCancelButtonShown = False
        progress.show(TITLE, "Exporting all drawing sheets to PDF...", 0, 2, 0)
        _export_pdf(document, pdf_path, drawing_api)
        pdf_saved = True
        progress.progressValue = 1
        progress.message = (
            "Converting PDF pages. First run may download the image tools..."
        )
        images = _convert_images(pdf_path, image_format, bool(existing))
        progress.hide()
        ui.messageBox(
            f"Saved PDF:\n{pdf_path}\n\nCreated {len(images)} image(s) at 300 DPI "
            "in the same folder.",
            TITLE,
        )
    except Exception:
        if progress:
            progress.hide()
        prefix = (
            f"PDF saved successfully:\n{pdf_path}\n\nImage conversion failed. "
            "The PDF has been kept.\n\n"
            if pdf_saved
            else "Drawing export failed.\n\n"
        )
        ui.messageBox(prefix + traceback.format_exc(), TITLE)
    finally:
        if progress:
            progress.hide()
