# Export Drawing PDF and Images

A Fusion script that exports all drawing sheets to one PDF and then creates a PNG, JPEG, or both for every sheet at 300 DPI.

## Install and run

1. Download the repository source for your chosen `ExportDrawingPDF-vX.Y.Z` release from [GitHub Releases](https://github.com/ScottGibb/Fusion-360-CAD-Exporter/releases), or check out that tag in a clone. Extract the download into a permanent location and locate its `ExportDrawingPDF` subfolder, including `pdf_to_images.py`.
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already installed.
3. In Fusion, press **Shift+S**, select **Scripts**, click **+**, and choose the repository's `ExportDrawingPDF` subfolder.
4. Open your drawing, make its tab active, select **ExportDrawingPDF**, and click **Run**.
5. Choose `png`, `jpeg`, or `both`, then the PDF save location. Images are written beside the PDF with numbered sheet names.

The script uses Fusion's drawing PDF export API. Image conversion runs locally through uv; its Python dependencies are downloaded automatically on first use. Standard uv locations are detected; a custom executable can be specified through `FUSION_EXPORT_UV`.

If image conversion fails, the PDF is kept. From this folder, an existing PDF can also be converted independently:

```sh
uv run --script pdf_to_images.py "/path/to/drawing.pdf" --format both --dpi 300
```

Add `--overwrite` to replace existing numbered images. Surplus images from sheets removed since a previous export are retained, so choose a new versioned filename or a fresh folder for a changed revision.

The script has its own version and release history. See `version.txt` and `CHANGELOG.md` in this folder.
