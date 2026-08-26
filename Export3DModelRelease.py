import adsk.core
import adsk.fusion
import adsk.drawing
import json
import os
import traceback
from datetime import datetime, timezone

handlers = []
COMMAND_ID = 'Export3DModelReleaseCommand'
COMMAND_NAME = 'Export 3D Model Release'


def _drawing_documents(app):
    # Fusion does not expose a reliable drawing marker without activating a
    # document. List open documents and validate the selected one as a drawing
    # immediately before exporting.
    return [app.documents.item(i) for i in range(app.documents.count)]


class CommandCreated(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        command = args.command
        inputs = command.commandInputs
        inputs.addStringValueInput('releaseName', 'Release name', '')
        inputs.addStringValueInput('version', 'Version', '1')
        inputs.addStringValueInput('folder', 'Release folder', '')
        selected = inputs.addSelectionInput('components', 'Printable components',
                                             'Select each component to export as STL')
        selected.addSelectionFilter('Occurrences')
        selected.setSelectionLimits(1, 0)
        app = adsk.core.Application.get()
        drawings = _drawing_documents(app)
        choice = inputs.addDropDownCommandInput('drawing', 'Open drawing',
            adsk.core.DropDownStyles.TextListDropDownStyle)
        for doc in drawings:
            choice.listItems.add(doc.name, choice.listItems.count == 0, doc.name)
        execute = Execute()
        command.execute.add(execute)
        handlers.append(execute)


class Execute(adsk.core.CommandEventHandler):
    def notify(self, args):
        ui = None
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            inputs = args.command.commandInputs
            name = inputs.itemById('releaseName').value.strip()
            version = inputs.itemById('version').value.strip()
            folder = inputs.itemById('folder').value.strip()
            selection = inputs.itemById('components')
            drawing_input = inputs.itemById('drawing')
            if not name or not version or not folder or selection.selectionCount == 0:
                raise ValueError('Release name, version, folder, and at least one printable component are required.')
            if drawing_input.selectedItem is None:
                raise ValueError('Open the associated drawing before exporting; a drawing PDF is required.')
            if os.path.isdir(folder) and os.listdir(folder):
                answer = ui.messageBox('The release folder is not empty. Replace files for this version?', COMMAND_NAME,
                    adsk.core.MessageBoxButtonTypes.YesNoButtonType)
                if answer != adsk.core.DialogResults.DialogYes:
                    return
            os.makedirs(folder, exist_ok=True)
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design:
                raise ValueError('Activate the saved Fusion design before running this command.')
            if not app.activeDocument.dataFile:
                raise ValueError('Save the Fusion design before exporting.')
            prefix = f'{name}-v{version}'
            manager = design.exportManager
            for index in range(selection.selectionCount):
                occurrence = adsk.fusion.Occurrence.cast(selection.selection(index).entity)
                component_name = ''.join(char if char.isalnum() or char in '-_' else '-' for char in occurrence.name)
                options = manager.createSTLExportOptions(occurrence, os.path.join(folder, f'{prefix}-{component_name}'))
                options.sendToPrintUtility = False
                if not manager.execute(options):
                    raise RuntimeError(f'STL export failed for {occurrence.name}')
            step = manager.createSTEPExportOptions(os.path.join(folder, f'{prefix}-assembly.step'), design.rootComponent)
            archive = manager.createFusionArchiveExportOptions(os.path.join(folder, prefix), design.rootComponent)
            if not manager.execute(step) or not manager.execute(archive):
                raise RuntimeError('Assembly STEP or Fusion archive export failed.')
            selected_drawing = drawing_input.selectedItem.name
            drawing_doc = next(doc for doc in _drawing_documents(app) if doc.name == selected_drawing)
            design_doc = app.activeDocument
            drawing_doc.activate()
            drawing = adsk.drawing.Drawing.cast(app.activeProduct)
            if not drawing:
                raise ValueError('The selected open document is not a Fusion drawing.')
            drawing_options = drawing.exportManager.createPDFExportOptions(os.path.join(folder, f'{prefix}-drawing.pdf'))
            if not drawing.exportManager.execute(drawing_options):
                raise RuntimeError('Drawing PDF export failed.')
            design_doc.activate()
            source = design_doc.dataFile
            export_record = {
                'source_design': {'id': source.id, 'version': source.versionNumber, 'name': source.name},
                'selected_components': [selection.selection(i).entity.name for i in range(selection.selectionCount)],
                'exported_at': datetime.now(timezone.utc).isoformat()
            }
            with open(os.path.join(folder, 'fusion-export.json'), 'w', encoding='utf-8') as record:
                json.dump(export_record, record, indent=2)
            ui.messageBox(f'Release exports completed in:\n{folder}\n\nRun build_release.py to validate the pack.', COMMAND_NAME)
        except Exception:
            if ui:
                ui.messageBox('Export failed:\n{}'.format(traceback.format_exc()), COMMAND_NAME)


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    command = ui.commandDefinitions.itemById(COMMAND_ID)
    if command:
        command.deleteMe()
    command = ui.commandDefinitions.addButtonDefinition(COMMAND_ID, COMMAND_NAME,
        'Export STL, STEP, F3D, and drawing PDF for a versioned release.')
    created = CommandCreated()
    command.commandCreated.add(created)
    handlers.append(created)
    panel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
    panel.controls.addCommand(command)


def stop(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    control = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel').controls.itemById(COMMAND_ID)
    if control:
        control.deleteMe()
    command = ui.commandDefinitions.itemById(COMMAND_ID)
    if command:
        command.deleteMe()
