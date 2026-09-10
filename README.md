# Fusion 360 CAD Exporter

[![MegaLinter](https://github.com/ScottGibb/Fusion-360-CAD-Exporter/actions/workflows/mega-linter.yaml/badge.svg)](https://github.com/ScottGibb/Fusion-360-CAD-Exporter/actions/workflows/mega-linter.yaml)

Two Fusion export tools maintained together in one repository and released with a shared version.

| Tool                                               | Run from                   | Outputs                                                                                             |
| -------------------------------------------------- | -------------------------- | --------------------------------------------------------------------------------------------------- |
| [Export 3D Model Release](Export3DModelRelease/)   | A design, **Add-Ins** tab  | Assembly F3D, STEP and STL, individual body STLs, transparent preview PNG, and `fusion-export.json` |
| [Export Drawing PDF and Images](ExportDrawingPDF/) | A drawing, **Scripts** tab | One PDF containing every sheet, plus a PNG, JPEG, or both for each sheet                            |

## Repository Layout

```text
Fusion-360-CAD-Exporter/
├── Export3DModelRelease/
│   ├── Export3DModelRelease.py
│   └── Export3DModelRelease.manifest
├── ExportDrawingPDF/
│   ├── ExportDrawingPDF.py
│   ├── ExportDrawingPDF.manifest
│   └── pdf_to_images.py
├── tests/
├── .github/
└── version.txt
```

Each tool folder is self-contained and can be registered separately in Fusion. Keep its Python files and manifest together.

## Installation

1. Clone or download this repository to a permanent folder, such as `Projects/Fusion-360-CAD-Exporter`.
2. In Fusion, open **Utilities > Scripts and Add-Ins** or press **Shift+S**.
3. On the **Add-Ins** tab, click **+** and select this repository's `Export3DModelRelease` folder. Select the add-in and click **Run**.
4. On the **Scripts** tab, click **+** and select this repository's `ExportDrawingPDF` folder. Run it when a drawing is active.
5. For drawing image conversion, install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available.

Alternatively, place `Export3DModelRelease` in Fusion's `API/AddIns` directory and `ExportDrawingPDF` in `API/Scripts`. For a development checkout, those entries can be symbolic links to the tool folders, so repository updates are picked up from the same source files.

After updating the model add-in, stop it and run it again to load the latest code. The drawing script loads when you run it.

### Upgrading from the original single-tool layout

The model entry point and manifest have moved from the repository root into `Export3DModelRelease/`. Point the existing Fusion add-in registration at that subfolder, or update its `API/AddIns/Export3DModelRelease` link to the subfolder. Register `ExportDrawingPDF/` on the **Scripts** tab.

## Model Release Export

1. Open and save your design in Fusion.
2. Go to **Solid > Scripts and Add-Ins** and click **Export 3D Model Release**.
3. Choose the export folder and click **OK**.

Output filenames use the saved design's name and version, for example `Bracket-v3-assembly.step`. The exporter traverses nested components and exports every visible solid body as an individual STL, alongside the assembly files and export metadata.

The preview is a transparent PNG. Capture temporarily hides joints, joint origins, sketches, construction geometry, canvases, analysis displays, the layout grid, and selection highlights throughout the assembly. It restores the camera, visibility, and selections afterward, including when capture fails. Model body visibility and decals retain their existing appearance.

## Drawing PDF and Images

1. Open your drawing and make its tab active.
2. Run **ExportDrawingPDF** from the **Scripts** tab.
3. Enter `png`, `jpeg`, or `both` (the default).
4. Choose where to save the PDF. The suggested filename includes the saved drawing's version.
5. Wait for the completion message. The PDF and numbered sheet images are saved together:

```text
Bracket-v3-drawing.pdf
Bracket-v3-drawing-sheet-001.png
Bracket-v3-drawing-sheet-001.jpg
Bracket-v3-drawing-sheet-002.png
Bracket-v3-drawing-sheet-002.jpg
```

All drawing sheets are included, with line weights, white image backgrounds, and 300 DPI resolution. Existing matching exports require confirmation before replacement. Surplus images from sheets removed since the previous export are retained; use a new versioned filename or a fresh folder when exporting a changed revision.

The script uses Autodesk's [drawing PDF export API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportPDFSample_Sample.htm) and requires a Fusion version and licence that permit drawing PDF export. It does not automate the operating system's print dialog.

The first conversion may download Python and the PDFium/Pillow dependencies through uv. Conversion runs locally in an isolated environment. Fusion's embedded Python needs no extra packages. Standard uv installation locations are detected even when Fusion starts from the Dock; a custom executable can be provided through `FUSION_EXPORT_UV`.

If image conversion fails, the successfully exported PDF is kept and the error is shown. To convert an existing PDF separately:

```sh
uv run --script ExportDrawingPDF/pdf_to_images.py "/path/to/drawing.pdf" --format both --dpi 300
```

Use `--overwrite` to replace existing numbered images, or `--dpi` to choose a resolution between 72 and 600.

## Development and Releases

Run the checks from the repository root:

```sh
python3 -B -m unittest discover -s tests -v
uv run --script tests/test_pdf_images.py
ruff check --no-cache Export3DModelRelease ExportDrawingPDF tests .github/scripts
ruff format --check --no-cache Export3DModelRelease ExportDrawingPDF tests .github/scripts
```

The unittest suite checks Fusion adapters with a simulated API and verifies the shared release updater. The uv command checks real multipage PDF rendering and file preservation. These checks do not replace running the tools inside Fusion.

Release Please maintains `version.txt` and `CHANGELOG.md`. The manifest updater applies that shared version to both tool manifests:

```sh
python3 .github/scripts/update-manifest.py
```

The updater resolves the repository from its own location, so it also works when invoked from another directory. `VERSION_FILE_PATH` overrides the version source; `MANIFEST_FILE_PATH` retains the option to update a single custom manifest. Both tools remain part of the same release and repository history.
