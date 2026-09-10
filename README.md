# Fusion 360 CAD Exporter

[![MegaLinter](https://github.com/ScottGibb/Fusion-360-CAD-Exporter/actions/workflows/mega-linter.yaml/badge.svg)](https://github.com/ScottGibb/Fusion-360-CAD-Exporter/actions/workflows/mega-linter.yaml)

Two Fusion export tools maintained in one repository and released independently. Each tool has its own version, changelog, release PR, Git tag, and GitHub release. Download the repository at a chosen release and register the tool folders in Fusion.

| Tool                                               | Run from                   | Outputs                                                                                             |
| -------------------------------------------------- | -------------------------- | --------------------------------------------------------------------------------------------------- |
| [Export 3D Model Release](Export3DModelRelease/)   | A design, **Add-Ins** tab  | Assembly F3D, STEP and STL, individual body STLs, transparent preview PNG, and `fusion-export.json` |
| [Export Drawing PDF and Images](ExportDrawingPDF/) | A drawing, **Scripts** tab | One PDF containing every sheet, plus a PNG, JPEG, or both for each sheet                            |

## Repository Layout

```text
Fusion-360-CAD-Exporter/
├── Export3DModelRelease/
│   ├── Export3DModelRelease.py
│   ├── Export3DModelRelease.manifest
│   ├── version.txt
│   ├── CHANGELOG.md
│   └── README.md
├── ExportDrawingPDF/
│   ├── ExportDrawingPDF.py
│   ├── ExportDrawingPDF.manifest
│   ├── pdf_to_images.py
│   ├── version.txt
│   ├── CHANGELOG.md
│   └── README.md
├── tests/
├── .github/
├── release-please-config.json
└── .release-please-manifest.json
```

Each tool folder is self-contained and can be registered separately in Fusion. Keep its Python files and manifest together.

## Installation

1. Open [GitHub Releases](https://github.com/ScottGibb/Fusion-360-CAD-Exporter/releases), choose the version you want, and download its **Source code** archive. Alternatively, clone the repository and check out that release's tag.
2. Extract the repository into a permanent folder, such as `Projects/Fusion-360-CAD-Exporter`. Keep the complete repository together; it contains both tools.
3. In Fusion, open **Utilities > Scripts and Add-Ins** or press **Shift+S**.
4. On the **Add-Ins** tab, click **+** and select the `Export3DModelRelease` subfolder inside the downloaded repository. Select the add-in and click **Run**.
5. On the **Scripts** tab, click **+** and select the `ExportDrawingPDF` subfolder inside the same repository. Run it when a drawing is active.
6. For drawing image conversion, install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available.

Alternatively, place `Export3DModelRelease` in Fusion's `API/AddIns` directory and `ExportDrawingPDF` in `API/Scripts`. For a development checkout, those entries can be symbolic links to the tool folders, so repository updates are picked up from the same source files.

To update, stop the model add-in, download the desired repository version, and replace the files at the same location. If you use a different folder, update the Fusion registrations to point at its tool subfolders. Run the add-in again to load the updated code. The drawing script loads when you run it.

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

## Independent Releases

Release Please manages a separate GitHub release for each tool:

| Tool | Version and changelog | Release tag |
| --- | --- | --- |
| Model add-in | `Export3DModelRelease/version.txt` and `CHANGELOG.md` in that folder | `Export3DModelRelease-vX.Y.Z` |
| Drawing script | `ExportDrawingPDF/version.txt` and `CHANGELOG.md` in that folder | `ExportDrawingPDF-vX.Y.Z` |

Choose a release with the prefix for the tool you want to install or update. Each release's source download contains the entire repository at that tag, including both tool folders. Each folder's `version.txt` identifies the included tool version; the tools can have different versions in the same download. Follow the installation steps above to register either or both folders in Fusion.

Each tool starts from its existing version, **1.2.0**, and evolves independently. The previous model release history is preserved in `Export3DModelRelease/CHANGELOG.md`; the old `v1.x` tags remain historical releases. Those older tags use the original layout with only the model add-in at the repository root. Choose a new component release for the two-tool layout.

### Maintaining releases

Use Conventional Commits for changes inside the appropriate tool folder, for example `fix(Export3DModelRelease): hide joint markers` or `feat(ExportDrawingPDF): add an image option`. Release Please assigns changes by file path. A change to one tool can release that tool alone; a change affecting both can create two release PRs. Changes confined to shared workflows or root documentation do not by themselves require a tool release.

On pushes to `main`, the Release Please workflow uses `release-please-config.json` and `.release-please-manifest.json` to open or update each tool's release PR. Merging a release PR updates that tool's `version.txt`, `CHANGELOG.md`, Fusion `.manifest` version, and release manifest entry, then creates its Git tag and GitHub release. The existing `MY_RELEASE_PLEASE_TOKEN` secret is used for release PRs and releases.

The release workflow handles versioning and GitHub releases only. GitHub provides the repository source downloads for each tag. The bootstrap commit in the configuration starts the new release histories immediately before the drawing script was introduced. New component releases become available after this configuration and the resulting release PRs are merged.
