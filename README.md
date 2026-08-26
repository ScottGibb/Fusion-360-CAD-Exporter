# Fusion 360 Release Exporter

[![MegaLinter](https://github.com/ScottGibb/Fusion-360-CAD-Exporter/actions/workflows/mega-linter.yaml/badge.svg)](https://github.com/ScottGibb/Fusion-360-CAD-Exporter/actions/workflows/mega-linter.yaml)

A Fusion 360 add-in that exports a complete design release package with one click, outputting assembly-level archives and individual body STLs ready for 3D printing.

---

## Key Features

* **Full Assembly Exports:** Generates a native Fusion archive (`.f3d`), a `.step` model, and a merged `.stl`.
* **Per-Body STL Exports:** Traverses all components, sub-assemblies, and occurrences at any nesting depth to export every visible solid body as an individual `.stl`.
* **Automated Versioning:** Automatically prefixes all output files with the saved design's name and native Fusion version number (e.g., `MyModel-v3-Assembly.step`).
* **Release Manifest:** Writes a `fusion-export.json` file alongside the models containing export metadata, design IDs, and body lists.
* **Native Folder Picker:** Select output directories directly through Fusion's UI dialog.

---

## Installation

1. Copy the project folder into your Fusion 360 `AddIns` directory:
   * **macOS:** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
   * **Windows:** `%appdata%\Autodesk\Autodesk Fusion 360\API\AddIns\`
2. Open Fusion 360 and navigate to **Utilities** > **Scripts and Add-Ins** (or press `Shift + S`).
3. Select the **Add-Ins** tab, choose **Export3DModelRelease**, and click **Run**.

---

## Usage

1. Open and save your target design in Fusion 360.
2. Go to **Solid** > **Scripts and Add-Ins** panel and click **Export 3D Model Release**.
3. Click **Choose export folder...** to pick your destination directory.
4. Click **OK** to run the export.
