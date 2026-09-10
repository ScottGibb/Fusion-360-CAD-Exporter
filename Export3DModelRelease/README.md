# Export 3D Model Release

A Fusion add-in that exports a saved design as assembly F3D, STEP and STL files, individual visible-body STLs, a transparent preview PNG, and `fusion-export.json`.

## Install and run

1. Download the repository source for your chosen `Export3DModelRelease-vX.Y.Z` release from [GitHub Releases](https://github.com/ScottGibb/Fusion-360-CAD-Exporter/releases), or check out that tag in a clone. Extract the download into a permanent location and locate its `Export3DModelRelease` subfolder.
2. In Fusion, press **Shift+S**, select **Add-Ins**, click **+**, and choose the repository's `Export3DModelRelease` subfolder.
3. Select **Export3DModelRelease** and click **Run**.
4. Open and save your design. Click **Export 3D Model Release** in **Solid > Scripts and Add-Ins**, choose an export folder, and click **OK**.

Stop the add-in before updating the repository files, then run it again. If the repository moves to a new folder, update the Fusion registration to point at its `Export3DModelRelease` subfolder.

Capture hides joints, joint origins, sketches, construction geometry, canvases, analyses, the grid, and selection highlights throughout the assembly. The original view settings are restored afterward.

The add-in has its own version and release history. See `version.txt` and `CHANGELOG.md` in this folder.
