"""Fusion 360 add-in: export a full design release.

Adds a command to the Solid > Scripts and Add-Ins panel that, for the
active design, exports:

* The whole assembly as a Fusion archive (.f3d), a STEP file, and a
  merged STL.
* Every solid body in the design as its own STL, ready for 3D printing —
  bodies sitting directly in the root component and bodies inside any
  occurrence, at any nesting depth.
* A high-resolution preview image (.png) with origin planes hidden,
  fitted to view, and with a transparent background.

The export destination is chosen through Fusion's native folder
browser rather than typed in by hand.
"""

import adsk.core
import adsk.fusion
import json
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

handlers: List[adsk.core.EventHandler] = []
COMMAND_ID = "Export3DModelReleaseCommand"
COMMAND_NAME = "Export 3D Model Release"

# Holds the folder chosen via the file explorer dialog for the current
# command invocation. Command inputs have no native "browse" widget, so a
# button input triggers the dialog and the result is stashed here for
# Execute to read.
_selected_folder: Dict[str, str] = {"path": ""}


def _sanitize_filename(text: str) -> str:
    """Replace characters that are unsafe in filenames with a hyphen.

    Args:
        text: Raw name (a design, component, or body name) that may
            contain spaces or other characters unsafe for filenames.

    Returns:
        text with every character that isn't alphanumeric, '-', or '_'
        replaced by '-'.
    """
    return "".join(char if char.isalnum() or char in "-_" else "-" for char in text)


class CommandCreated(adsk.core.CommandCreatedEventHandler):
    """Builds the command dialog: just the folder-browse button, wiring up
    the InputChanged/Execute handlers. The release name and version come
    from the design's own saved file, so no fields for them are needed.
    """

    def notify(self, args: adsk.core.CommandCreatedEventArgs) -> None:
        """Populate the command dialog's inputs.

        Args:
            args: Event args for the command-created event; args.command
                is the new command whose commandInputs are populated here.
        """
        command: adsk.core.Command = args.command
        inputs: adsk.core.CommandInputs = command.commandInputs

        # "Browse..." button (a non-checkbox BoolValueInput renders as a
        # button) plus a read-only text box that echoes the chosen path.
        inputs.addBoolValueInput(
            "chooseFolder", "Choose export folder...", False, "", False
        )
        inputs.addTextBoxCommandInput(
            "folderPath", "Export folder", "No folder selected", 2, True
        )

        _selected_folder["path"] = ""

        input_changed = InputChanged()
        command.inputChanged.add(input_changed)
        handlers.append(input_changed)

        execute = Execute()
        command.execute.add(execute)
        handlers.append(execute)


class InputChanged(adsk.core.InputChangedEventHandler):
    """Opens the folder browser when the "Choose export folder..." button
    is clicked, and writes the chosen path back into the dialog.
    """

    def notify(self, args: adsk.core.InputChangedEventArgs) -> None:
        """Handle a command-input change event.

        Only reacts to the 'chooseFolder' button; all other input changes
        are ignored.

        Args:
            args: Event args identifying which input changed
                (args.input) and its owning command
                (args.input.parentCommand).
        """
        changed_input: adsk.core.CommandInput = args.input
        if changed_input.id != "chooseFolder":
            return

        app: adsk.core.Application = adsk.core.Application.get()
        ui: adsk.core.UserInterface = app.userInterface
        dialog: adsk.core.FolderDialog = ui.createFolderDialog()
        dialog.title = "Choose export folder"

        if dialog.showDialog() == adsk.core.DialogResults.DialogOK:
            _selected_folder["path"] = dialog.folder
            folder_input: adsk.core.TextBoxCommandInput = (
                changed_input.parentCommand.commandInputs.itemById("folderPath")
            )
            folder_input.text = dialog.folder


class Execute(adsk.core.CommandEventHandler):
    """Runs the actual export once the user confirms the command dialog."""

    def notify(self, args: adsk.core.CommandEventArgs) -> None:
        """Validate inputs, then export the assembly and its parts.

        Exports, in order: a Fusion archive, a STEP file, a merged STL for
        the whole design, followed by one STL per solid body, a high-resolution
        transparent PNG render, then writes a small JSON manifest describing
        what was exported. The filename prefix is derived from the source
        design's saved file name and version rather than being typed in. Any
        failure is caught and shown in a message box rather than raised, since
        Fusion add-in commands have no console.

        Args:
            args: Event args for the command-execute event (unused
                directly; state is read from _selected_folder and from
                the active design's saved data file).
        """
        ui: adsk.core.UserInterface = None
        try:
            app: adsk.core.Application = adsk.core.Application.get()
            ui = app.userInterface
            folder: str = _selected_folder["path"]

            if not folder:
                raise ValueError("Choose an export folder before running the export.")

            design: adsk.fusion.Design = adsk.fusion.Design.cast(app.activeProduct)
            if not design:
                raise ValueError(
                    "Activate a Fusion design before running this command."
                )
            if not app.activeDocument.dataFile:
                raise ValueError("Save the Fusion design before exporting.")

            if os.path.isdir(folder) and os.listdir(folder):
                answer = ui.messageBox(
                    "The export folder is not empty. Replace files for this version?",
                    COMMAND_NAME,
                    adsk.core.MessageBoxButtonTypes.YesNoButtonType,
                )
                if answer != adsk.core.DialogResults.DialogYes:
                    return
            os.makedirs(folder, exist_ok=True)

            source: adsk.core.DataFile = app.activeDocument.dataFile
            prefix: str = f"{_sanitize_filename(source.name)}-v{source.versionNumber}"
            root: adsk.fusion.Component = design.rootComponent
            manager: adsk.fusion.ExportManager = design.exportManager

            _export_assembly(manager, root, folder, prefix)
            exported_bodies: List[str] = _export_bodies(manager, root, folder, prefix)

            preview_filename = f"{prefix}-preview.png"
            preview_path = os.path.join(folder, preview_filename)
            _capture_model_image(app, design, preview_path)

            _write_manifest(app, folder, exported_bodies, preview_filename)

            ui.messageBox(f"Release exports completed in:\n{folder}", COMMAND_NAME)
        except Exception:
            if ui:
                ui.messageBox(
                    "Export failed:\n{}".format(traceback.format_exc()), COMMAND_NAME
                )


def _capture_model_image(
    app: adsk.core.Application,
    design: adsk.fusion.Design,
    output_path: str,
    width: int = 1920,
    height: int = 1080,
) -> None:
    """Capture a PNG of the active model with hidden origin planes, transparent background, and fitted view.

    Temporarily turns off origin and construction geometry visibility on the
    root component, resizes the viewport camera to fit the full design, and
    saves an image file with background transparency enabled. Restores original
    visibility settings upon completion.

    Args:
        app: Fusion application instance.
        design: The active Fusion design.
        output_path: Full file path where the image will be written.
        width: Image width in pixels (default: 1920).
        height: Image height in pixels (default: 1080).

    Raises:
        RuntimeError: If image export execution fails.
    """
    viewport: adsk.core.Viewport = app.activeViewport
    root: adsk.fusion.Component = design.rootComponent

    was_origin_visible = root.isOriginFolderLightBulbOn
    was_construction_visible = root.isConstructionFolderLightBulbOn

    try:
        root.isOriginFolderLightBulbOn = False
        root.isConstructionFolderLightBulbOn = False

        viewport.fit()
        viewport.refresh()

        success = viewport.saveAsImageFile(output_path, width, height)
        if not success:
            raise RuntimeError("Failed to save viewport image.")
    finally:
        root.isOriginFolderLightBulbOn = was_origin_visible
        root.isConstructionFolderLightBulbOn = was_construction_visible
        viewport.refresh()


def _export_assembly(
    manager: adsk.fusion.ExportManager,
    root: adsk.fusion.Component,
    folder: str,
    prefix: str,
) -> None:
    """Export the whole design as a Fusion archive, STEP, and merged STL.

    Args:
        manager: The active design's export manager.
        root: The design's root component (exported as a single unit).
        folder: Destination directory for the exported files.
        prefix: Filename prefix, derived from the source file's name and version.

    Raises:
        RuntimeError: If any of the three exports fails.
    """
    archive_options = manager.createFusionArchiveExportOptions(
        os.path.join(folder, f"{prefix}-assembly"), root
    )
    step_options = manager.createSTEPExportOptions(
        os.path.join(folder, f"{prefix}-assembly.step"), root
    )
    assembly_stl_options = manager.createSTLExportOptions(
        root, os.path.join(folder, f"{prefix}-assembly")
    )
    assembly_stl_options.sendToPrintUtility = False

    if not manager.execute(archive_options):
        raise RuntimeError("Fusion archive export failed for the assembly.")
    if not manager.execute(step_options):
        raise RuntimeError("STEP export failed for the assembly.")
    if not manager.execute(assembly_stl_options):
        raise RuntimeError("STL export failed for the assembly.")


def _collect_bodies(
    root: adsk.fusion.Component,
) -> List[Tuple[str, adsk.fusion.BRepBody]]:
    """Find every solid body in the design, however it's organized.

    A component can hold several bodies, and exporting one STL per
    top-level occurrence would merge those bodies into a single file.
    This instead walks bodies sitting directly in the root component and
    bodies inside every occurrence — including nested sub-assemblies —
    so each individual body gets its own entry.

    Args:
        root: The design's root component.

    Returns:
        A list of (label, body) pairs, where label combines the owning
        component/occurrence name and the body's own name, e.g.
        'Bracket-Body1'.
    """
    bodies: List[Tuple[str, adsk.fusion.BRepBody]] = []

    for body in root.bRepBodies:
        if body.isSolid and body.isVisible:
            bodies.append((f"{root.name}-{body.name}", body))

    for occurrence in root.allOccurrences:
        if not occurrence.isVisible:
            continue
        for body in occurrence.bRepBodies:
            if body.isSolid and body.isVisible:
                bodies.append((f"{occurrence.name}-{body.name}", body))

    return bodies


def _export_bodies(
    manager: adsk.fusion.ExportManager,
    root: adsk.fusion.Component,
    folder: str,
    prefix: str,
) -> List[str]:
    """Export every solid body in the design as its own printable STL.

    Args:
        manager: The active design's export manager.
        root: The design's root component; every body reachable from it
            (its own bodies, plus bodies inside every occurrence at any
            nesting depth) is exported individually.
        folder: Destination directory for the exported files.
        prefix: Filename prefix, derived from the source file's name and version.

    Returns:
        The labels of the bodies that were exported, in export order.

    Raises:
        RuntimeError: If the STL export fails for any body.
    """
    exported_bodies: List[str] = []
    for label, body in _collect_bodies(root):
        safe_label: str = _sanitize_filename(label)
        options = manager.createSTLExportOptions(
            body, os.path.join(folder, f"{prefix}-{safe_label}")
        )
        options.sendToPrintUtility = False
        if not manager.execute(options):
            raise RuntimeError(f"STL export failed for {label}")
        exported_bodies.append(label)
    return exported_bodies


def _write_manifest(
    app: adsk.core.Application,
    folder: str,
    exported_bodies: List[str],
    preview_filename: str,
) -> None:
    """Write a JSON summary of the export next to the exported files.

    Args:
        app: The running Fusion application, used to read the source
            design's file metadata.
        folder: Destination directory; the manifest is written as
            'fusion-export.json' inside it.
        exported_bodies: Labels of the bodies exported as individual
            STLs, as returned by _export_bodies.
        preview_filename: Relative filename of the generated preview PNG image.
    """
    source: adsk.core.DataFile = app.activeDocument.dataFile
    export_record: Dict[str, Any] = {
        "source_design": {
            "id": source.id,
            "version": source.versionNumber,
            "name": source.name,
        },
        "preview_image": preview_filename,
        "exported_bodies": exported_bodies,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(
        os.path.join(folder, "fusion-export.json"), "w", encoding="utf-8"
    ) as record:
        json.dump(export_record, record, indent=2)


def run(context: Dict[str, Any]) -> None:
    """Add-in entry point: register the command and add it to the panel.

    Args:
        context: Fusion's add-in run context (unused).
    """
    app: adsk.core.Application = adsk.core.Application.get()
    ui: adsk.core.UserInterface = app.userInterface
    command_definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if command_definition:
        command_definition.deleteMe()
    command_definition = ui.commandDefinitions.addButtonDefinition(
        COMMAND_ID,
        COMMAND_NAME,
        "Export F3D, STEP, STL assembly/parts, and a transparent model snapshot.",
    )
    created = CommandCreated()
    command_definition.commandCreated.add(created)
    handlers.append(created)
    panel: adsk.core.ToolbarPanel = ui.allToolbarPanels.itemById(
        "SolidScriptsAddinsPanel"
    )
    panel.controls.addCommand(command_definition)


def stop(context: Dict[str, Any]) -> None:
    """Add-in teardown: remove the command from the panel and delete it.

    Args:
        context: Fusion's add-in stop context (unused).
    """
    app: adsk.core.Application = adsk.core.Application.get()
    ui: adsk.core.UserInterface = app.userInterface
    control = ui.allToolbarPanels.itemById("SolidScriptsAddinsPanel").controls.itemById(
        COMMAND_ID
    )
    if control:
        control.deleteMe()
    command_definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if command_definition:
        command_definition.deleteMe()
