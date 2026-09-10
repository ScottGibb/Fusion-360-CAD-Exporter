# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["pypdfium2>=4.30,<6", "Pillow>=11,<13"]
# ///
"""Render every PDF page locally; run with uv to isolate image dependencies."""

import argparse
import json
import os
from pathlib import Path
import tempfile


def convert_pdf(pdf_path, image_format="both", dpi=300, overwrite=False):
    """Create numbered white-background images beside a PDF, preserving it."""
    import pypdfium2 as pdfium

    pdf_path = Path(pdf_path).resolve(strict=True)
    if image_format not in {"png", "jpeg", "both"}:
        raise ValueError("Image format must be png, jpeg, or both.")
    if not 72 <= dpi <= 600:
        raise ValueError("DPI must be between 72 and 600.")
    extensions = (
        ("png", "jpg")
        if image_format == "both"
        else ("jpg" if image_format == "jpeg" else "png",)
    )
    outputs = []
    with pdfium.PdfDocument(str(pdf_path)) as document:
        if not len(document):
            raise ValueError("The PDF has no pages.")
        for number in range(1, len(document) + 1):
            for extension in extensions:
                outputs.append(
                    pdf_path.with_name(
                        f"{pdf_path.stem}-sheet-{number:03d}.{extension}"
                    )
                )
        existing = [path for path in outputs if path.exists()]
        if existing and not overwrite:
            raise FileExistsError(f"Image already exists: {existing[0]}")
        # Finish rendering all sheets before replacing any existing images.
        with tempfile.TemporaryDirectory(
            prefix=".drawing-images-", dir=pdf_path.parent
        ) as temp:
            for index in range(len(document)):
                page = document[index]
                try:
                    bitmap = page.render(
                        scale=dpi / 72, fill_color=(255, 255, 255, 255)
                    )
                    try:
                        image = bitmap.to_pil().convert("RGB")
                        try:
                            for extension in extensions:
                                target = (
                                    Path(temp)
                                    / f"{pdf_path.stem}-sheet-{index + 1:03d}.{extension}"
                                )
                                options = {"dpi": (dpi, dpi)}
                                if extension == "jpg":
                                    options.update(quality=95, subsampling=0)
                                image.save(target, **options)
                        finally:
                            image.close()
                    finally:
                        bitmap.close()
                finally:
                    page.close()
            for target in outputs:
                source = Path(temp) / target.name
                if overwrite:
                    os.replace(source, target)
                else:
                    # Exclusive creation also protects against a collision
                    # introduced after the initial existence check.
                    with target.open("xb") as destination:
                        destination.write(source.read_bytes())
    return [str(path) for path in outputs]


def main():
    """CLI entry point, also used by the Fusion script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--format", choices=("png", "jpeg", "both"), default="both")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(json.dumps(convert_pdf(args.pdf, args.format, args.dpi, args.overwrite)))


if __name__ == "__main__":
    main()
