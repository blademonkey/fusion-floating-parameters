import adsk.core
import adsk.fusion
import json
import os
from pathlib import Path
import traceback


APP = adsk.core.Application.get()
UI = APP.userInterface
ADDIN_DIR = os.path.dirname(os.path.realpath(__file__))

PALETTE_ID = 'blademonkeyFloatingParametersPalette'
COMMAND_ID = 'blademonkeyFloatingParametersCommand'
COMMAND_NAME = 'Floating Parameters'
COMMAND_DESCRIPTION = 'Show or hide the Floating Parameters palette.'
COMMAND_RESOURCE_DIR = os.path.join(ADDIN_DIR, 'resources', 'command')

handlers = []
document_activated_handler = None
active_selection_handler = None
workspace_activated_handler = None
command_created_handler = None
bloodhound_enabled = False
ui_initialization_pending = False
initial_palette_open_pending = False


def _log(message):
    try:
        APP.log('Floating Parameters: {}'.format(message))
    except Exception:
        pass


def _design():
    return adsk.fusion.Design.cast(APP.activeProduct)


def _safe_parameter_attr(parameter, name, default=''):
    try:
        value = getattr(parameter, name)
        return default if value is None else value
    except Exception:
        return default


def _parameter_kind(parameter):
    """Return a stable palette kind without assuming every parameter is numeric."""
    try:
        value_type = parameter.valueType
        value_types = getattr(adsk.fusion, 'ParameterValueTypes', None)
        numeric_type = getattr(value_types, 'NumericParameterValueType', None)
        text_type = getattr(value_types, 'TextParameterValueType', None)
        if numeric_type is not None and value_type == numeric_type:
            return 'numeric'
        if text_type is not None and value_type == text_type:
            return 'text'
    except Exception:
        # valueType and textValue were added in September 2025. Fall back to
        # guarded property probes for resilience across Fusion builds.
        pass

    try:
        parameter.value
        return 'numeric'
    except Exception:
        pass

    try:
        parameter.textValue
        return 'text'
    except Exception:
        return 'unsupported'


def _read_parameter(parameter, units_manager):
    kind = _parameter_kind(parameter)
    name = str(_safe_parameter_attr(parameter, 'name', 'Unknown parameter'))
    expression = str(_safe_parameter_attr(parameter, 'expression', ''))
    unit = str(_safe_parameter_attr(parameter, 'unit', ''))
    comment = str(_safe_parameter_attr(parameter, 'comment', ''))

    payload = {
        'name': name,
        'kind': kind,
        'expression': expression,
        'value': None,
        'valueText': '',
        'displayValue': '',
        'textValue': '',
        'unit': unit,
        'comment': comment,
        'editable': kind == 'numeric'
    }

    if kind == 'numeric':
        value = parameter.value
        try:
            value_text = units_manager.formatInternalValue(value, unit, True)
        except Exception:
            value_text = str(value)
        payload.update({
            'value': value,
            'valueText': value_text,
            'displayValue': expression or value_text
        })
    elif kind == 'text':
        text_value = str(_safe_parameter_attr(parameter, 'textValue', ''))
        payload.update({
            'valueText': text_value,
            'displayValue': text_value,
            'textValue': text_value
        })
    else:
        payload.update({
            'valueText': 'Unsupported',
            'displayValue': 'Unsupported'
        })

    return payload


def _parameter_payload(source='system'):
    design = _design()
    if not design:
        return {
            'ok': False,
            'message': 'Open a Fusion design to view its user parameters.',
            'document': '',
            'source': source,
            'defaultUnits': '',
            'parameters': []
        }

    parameters = []
    user_parameters = design.userParameters
    units_manager = design.unitsManager
    for index in range(user_parameters.count):
        try:
            parameter = user_parameters.item(index)
        except Exception as exc:
            APP.log('Could not access user parameter {}: {}'.format(index, exc))
            continue

        try:
            parameters.append(_read_parameter(parameter, units_manager))
        except Exception as exc:
            name = str(_safe_parameter_attr(parameter, 'name', f'Parameter {index + 1}'))
            APP.log('Could not read user parameter "{}": {}'.format(name, exc))
            parameters.append({
                'name': name,
                'kind': 'unsupported',
                'expression': '',
                'value': None,
                'valueText': 'Unsupported',
                'displayValue': 'Unsupported',
                'textValue': '',
                'unit': '',
                'comment': '',
                'editable': False
            })

    document_name = APP.activeDocument.name if APP.activeDocument else 'Untitled'
    return {
        'ok': True,
        'message': '' if parameters else 'This design has no user parameters yet.',
        'document': document_name,
        'source': source,
        'defaultUnits': units_manager.defaultLengthUnits,
        'parameters': parameters
    }


def _send(action, payload):
    palette = UI.palettes.itemById(PALETTE_ID)
    if palette:
        palette.sendInfoToHTML(action, json.dumps(payload))


def _refresh(source='system'):
    _send('parameters', _parameter_payload(source))


def _empty_highlight(selection_count=0, selection_supported=False):
    return {
        'direct': [],
        'selectionSupported': selection_supported,
        'selectionCount': selection_count
    }


def _selection_items(selection_source):
    if selection_source is None:
        return []

    count = getattr(selection_source, 'count', None)
    item = getattr(selection_source, 'item', None)
    if isinstance(count, int) and callable(item):
        return [item(index) for index in range(count)]

    try:
        return list(selection_source)
    except Exception:
        return []


def _native_object(entity):
    if not entity:
        return None
    try:
        native = getattr(entity, 'nativeObject', None)
        return native or entity
    except Exception:
        return entity


def _same_entity(left, right):
    if not left or not right:
        return False
    try:
        if left == right:
            return True
    except Exception:
        pass

    native_left = _native_object(left)
    native_right = _native_object(right)
    try:
        return native_left == native_right
    except Exception:
        return False


def _unwrap_timeline_object(entity):
    timeline_object = adsk.fusion.TimelineObject.cast(entity)
    if timeline_object and not timeline_object.isGroup:
        return timeline_object.entity
    return entity


def _direct_user_parameter_names(model_parameters):
    names = set()
    for model_parameter in model_parameters:
        if not model_parameter:
            continue
        dependencies = model_parameter.dependencyParameters
        for index in range(dependencies.count):
            dependency = dependencies.item(index)
            if adsk.fusion.UserParameter.cast(dependency):
                names.add(dependency.name)
    return names


def _resolve_selection_entity(entity):
    entity = _unwrap_timeline_object(entity)
    if not entity:
        return False, set()

    sketch_dimension = adsk.fusion.SketchDimension.cast(entity)
    if sketch_dimension:
        parameter = sketch_dimension.parameter
        return True, _direct_user_parameter_names([parameter] if parameter else [])

    feature = adsk.fusion.Feature.cast(entity)
    if not feature:
        return False, set()

    model_parameters = []
    component_parameters = feature.parentComponent.modelParameters
    for index in range(component_parameters.count):
        model_parameter = component_parameters.item(index)
        if _same_entity(model_parameter.createdBy, feature):
            model_parameters.append(model_parameter)

    return True, _direct_user_parameter_names(model_parameters)


def _bloodhound_payload(selection_source=None):
    if not _design():
        return _empty_highlight()

    selections = _selection_items(
        UI.activeSelections if selection_source is None else selection_source
    )
    direct_names = set()
    supported = False

    for selection in selections:
        try:
            entity_supported, names = _resolve_selection_entity(selection.entity)
            supported = supported or entity_supported
            direct_names.update(names)
        except Exception as exc:
            APP.log('Bloodhound could not resolve a selection: {}'.format(exc))

    return {
        'direct': sorted(direct_names, key=str.casefold),
        'selectionSupported': supported,
        'selectionCount': len(selections)
    }


def _update_bloodhound(selection_source=None):
    if not bloodhound_enabled:
        return
    _send('highlight', _bloodhound_payload(selection_source))


def _set_bloodhound_enabled(enabled):
    global bloodhound_enabled
    bloodhound_enabled = bool(enabled)
    _send('bloodhoundState', {'enabled': bloodhound_enabled})
    if bloodhound_enabled:
        _update_bloodhound()
    else:
        _send('highlight', _empty_highlight())


def _apply_updates(updates):
    design = _design()
    if not design:
        return {'ok': False, 'message': 'No active Fusion design.', 'errors': {}}

    errors = {}
    changed = 0
    user_parameters = design.userParameters

    for update in updates:
        name = str(update.get('name', '')).strip()
        expression = str(update.get('expression', '')).strip()
        if not name:
            continue

        parameter = user_parameters.itemByName(name)
        if not parameter:
            errors[name] = 'The parameter no longer exists.'
            continue
        if _parameter_kind(parameter) != 'numeric':
            errors[name] = 'This parameter type is read-only in Floating Parameters.'
            continue
        if not expression:
            errors[name] = 'Expression cannot be empty.'
            continue

        try:
            if parameter.expression != expression:
                parameter.expression = expression
                changed += 1
        except Exception as exc:
            errors[name] = str(exc) or 'Fusion rejected this expression.'

    compute_error = None
    try:
        compute_result = design.computeAll()
        if compute_result is False:
            compute_error = 'Fusion reported that the design could not be recomputed.'
    except Exception as exc:
        compute_error = str(exc) or 'Design failed to recompute.'

    message = (
        f'Updated {changed} parameter' + ('' if changed == 1 else 's') + '.'
    )
    if errors:
        message = f'Updated {changed}; {len(errors)} could not be applied.'
    if compute_error:
        message += f' Recompute failed: {compute_error}'

    return {
        'ok': not errors and not compute_error,
        'message': message,
        'errors': errors,
        'data': _parameter_payload()
    }


def _create_parameter(data):
    design = _design()
    if not design:
        return {
            'ok': False,
            'message': 'Open a Fusion design before creating a parameter.'
        }

    name = str(data.get('name', '')).strip()
    expression = str(data.get('expression', '')).strip()
    units = str(data.get('units', '')).strip()
    comment = str(data.get('comment', '')).strip()

    if not name:
        return {'ok': False, 'message': 'Parameter name is required.'}
    if not expression:
        return {'ok': False, 'message': 'Expression is required.'}
    if design.allParameters.itemByName(name):
        return {
            'ok': False,
            'message': f'A parameter named "{name}" already exists.'
        }

    try:
        value_input = adsk.core.ValueInput.createByString(expression)
        parameter = design.userParameters.add(
            name,
            value_input,
            units,
            comment
        )
        if not parameter:
            raise RuntimeError('Fusion did not create the parameter.')
    except Exception as exc:
        return {
            'ok': False,
            'message': str(exc) or 'Fusion rejected the new parameter.'
        }

    compute_error = None
    try:
        compute_result = design.computeAll()
        if compute_result is False:
            compute_error = 'Fusion reported that the design could not be recomputed.'
    except Exception as exc:
        compute_error = str(exc) or 'Design failed to recompute.'

    message = f'Created parameter "{name}".'
    if compute_error:
        message += f' Recompute failed: {compute_error}'

    return {
        'ok': not compute_error,
        'created': True,
        'message': message,
        'data': _parameter_payload('create')
    }


def _rename_parameter(data):
    design = _design()
    if not design:
        return {
            'ok': False,
            'renamed': False,
            'message': 'Open a Fusion design before renaming a parameter.'
        }

    old_name = str(data.get('oldName', '')).strip()
    new_name = str(data.get('newName', '')).strip()
    if not old_name:
        return {'ok': False, 'renamed': False, 'message': 'Original parameter name is required.'}
    if not new_name:
        return {'ok': False, 'renamed': False, 'message': 'Parameter name cannot be empty.'}

    parameter = design.userParameters.itemByName(old_name)
    if not parameter:
        return {
            'ok': False,
            'renamed': False,
            'message': f'The user parameter "{old_name}" no longer exists.'
        }
    if new_name == old_name:
        return {
            'ok': True,
            'renamed': False,
            'unchanged': True,
            'message': 'Parameter name was not changed.'
        }

    existing = design.allParameters.itemByName(new_name)
    if existing:
        return {
            'ok': False,
            'renamed': False,
            'message': f'A parameter named "{new_name}" already exists.'
        }

    try:
        parameter.name = new_name
        if parameter.name != new_name:
            raise RuntimeError('Fusion did not retain the requested parameter name.')
    except Exception as exc:
        return {
            'ok': False,
            'renamed': False,
            'message': str(exc) or 'Fusion rejected the new parameter name.'
        }

    compute_error = None
    try:
        compute_result = design.computeAll()
        if compute_result is False:
            compute_error = 'Fusion reported that the design could not be recomputed.'
    except Exception as exc:
        compute_error = str(exc) or 'Design failed to recompute.'

    message = f'Renamed "{old_name}" to "{new_name}".'
    if compute_error:
        message += f' Recompute failed: {compute_error}'

    return {
        'ok': not compute_error,
        'renamed': True,
        'oldName': old_name,
        'newName': new_name,
        'message': message,
        'data': _parameter_payload('rename')
    }


class PaletteHTMLHandler(adsk.core.HTMLEventHandler):
    def notify(self, args):
        try:
            data = json.loads(args.data) if args.data else {}
            if args.action in ('ready', 'refresh'):
                if args.action == 'ready':
                    _set_bloodhound_enabled(False)
                source = 'ready' if args.action == 'ready' else 'manual'
                _refresh(source)
                args.returnData = json.dumps({'ok': True})
            elif args.action == 'apply':
                result = _apply_updates(data.get('updates', []))
                _send('applyResult', result)
                args.returnData = json.dumps(result)
            elif args.action == 'applyOne':
                update = data.get('update', {})
                result = _apply_updates([update])
                result['name'] = str(update.get('name', '')).strip()
                _send('applyOneResult', result)
                args.returnData = json.dumps(result)
            elif args.action == 'create':
                result = _create_parameter(data)
                _send('createResult', result)
                args.returnData = json.dumps(result)
            elif args.action == 'rename':
                result = _rename_parameter(data)
                _send('renameResult', result)
                if result.get('renamed'):
                    _update_bloodhound()
                args.returnData = json.dumps(result)
            elif args.action == 'setBloodhound':
                _set_bloodhound_enabled(data.get('enabled') is True)
                args.returnData = json.dumps({
                    'ok': True,
                    'enabled': bloodhound_enabled
                })
            else:
                args.returnData = json.dumps({
                    'ok': False,
                    'message': f'Unknown action: {args.action}'
                })
        except Exception:
            error = traceback.format_exc()
            args.returnData = json.dumps({'ok': False, 'message': error})
            _send('fatalError', {'message': error})


class PaletteClosedHandler(adsk.core.UserInterfaceGeneralEventHandler):
    def notify(self, args):
        global initial_palette_open_pending
        initial_palette_open_pending = False
        _on_palette_hidden()


class ActiveSelectionChangedHandler(adsk.core.ActiveSelectionEventHandler):
    def notify(self, args):
        if not bloodhound_enabled:
            return
        try:
            _update_bloodhound(args.currentSelection)
        except Exception as exc:
            APP.log('Bloodhound selection event failed: {}'.format(exc))


class DocumentActivatedHandler(adsk.core.DocumentEventHandler):
    def notify(self, args):
        try:
            if ui_initialization_pending:
                _ensure_ui_initialized('documentActivated')
            palette = UI.palettes.itemById(PALETTE_ID)
            if palette and palette.isVisible:
                _send('highlight', _empty_highlight())
                _refresh('document')
                _update_bloodhound()
        except Exception as exc:
            _log('Document activation handling failed: {}'.format(exc))


class WorkspaceActivatedHandler(adsk.core.WorkspaceEventHandler):
    def notify(self, args):
        if not ui_initialization_pending:
            return
        try:
            _ensure_ui_initialized('workspaceActivated')
        except Exception as exc:
            _log('Workspace activation handling failed: {}'.format(exc))


def _ensure_palette_created():
    palette = UI.palettes.itemById(PALETTE_ID)
    if palette:
        return True

    # Palette.add expects a URL. Passing a native Windows path causes Fusion's
    # embedded browser to encode backslashes as %5C and reject the result.
    html_url = Path(
        os.path.join(ADDIN_DIR, 'resources', 'index.html')
    ).resolve().as_uri()
    try:
        palette = UI.palettes.add(
            PALETTE_ID,
            'Floating Parameters',
            html_url,
            False,
            True,
            True,
            460,
            640
        )
        if not palette:
            _log('Palette creation returned no palette for {}'.format(html_url))
            return False

        html_handler = PaletteHTMLHandler()
        palette.incomingFromHTML.add(html_handler)
        handlers.append(html_handler)

        closed_handler = PaletteClosedHandler()
        palette.closed.add(closed_handler)
        handlers.append(closed_handler)
        return True
    except Exception:
        _log('Palette creation failed for {}:\n{}'.format(html_url, traceback.format_exc()))
        try:
            if palette:
                palette.deleteMe()
        except Exception:
            pass
        return False


def _on_palette_hidden():
    global bloodhound_enabled
    bloodhound_enabled = False
    try:
        _send('bloodhoundState', {'enabled': False})
        _send('highlight', _empty_highlight())
    except Exception as exc:
        _log('Could not synchronize the hidden palette state: {}'.format(exc))


def _set_palette_visible(visible):
    palette = UI.palettes.itemById(PALETTE_ID)
    if not palette:
        _log('Cannot set palette visibility because the palette does not exist.')
        return False

    try:
        if not visible:
            _on_palette_hidden()
        palette.isVisible = bool(visible)
        if bool(palette.isVisible) != bool(visible):
            _log('Fusion did not retain palette visibility={}.'.format(bool(visible)))
            return False
        return True
    except Exception:
        _log('Could not set palette visibility={}:\n{}'.format(
            bool(visible), traceback.format_exc()
        ))
        return False


def _ensure_command_definition_and_handler():
    global command_created_handler
    try:
        command_definition = UI.commandDefinitions.itemById(COMMAND_ID)
        if not command_definition:
            command_definition = UI.commandDefinitions.addButtonDefinition(
                COMMAND_ID,
                COMMAND_NAME,
                COMMAND_DESCRIPTION,
                COMMAND_RESOURCE_DIR
            )
        else:
            command_definition.resourceFolder = COMMAND_RESOURCE_DIR

        if not command_definition:
            _log('Command definition creation returned no command.')
            return None

        if not command_created_handler:
            command_created_handler = CommandCreatedHandler()
            command_definition.commandCreated.add(command_created_handler)
            handlers.append(command_created_handler)
        return command_definition
    except Exception:
        _log('Command definition initialization failed:\n{}'.format(
            traceback.format_exc()
        ))
        return None


def _ensure_toolbar_control(command_definition):
    try:
        panel = UI.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        if not panel:
            active_workspace = getattr(UI, 'activeWorkspace', None)
            workspace_id = getattr(active_workspace, 'id', 'unavailable')
            _log('Toolbar panel is not ready; active workspace={}.'.format(workspace_id))
            return False

        control = panel.controls.itemById(COMMAND_ID)
        if not control:
            control = panel.controls.addCommand(command_definition)
        if not control:
            _log('Toolbar control creation returned no control.')
            return False

        control.isPromoted = True
        control.isPromotedByDefault = True
        return True
    except Exception:
        _log('Toolbar control initialization failed:\n{}'.format(
            traceback.format_exc()
        ))
        return False


def _ensure_ui_initialized(trigger='unknown'):
    global initial_palette_open_pending, ui_initialization_pending

    command_definition = _ensure_command_definition_and_handler()
    command_ready = command_definition is not None
    toolbar_ready = (
        _ensure_toolbar_control(command_definition) if command_ready else False
    )
    palette_ready = _ensure_palette_created()

    if initial_palette_open_pending and palette_ready:
        if _set_palette_visible(True):
            initial_palette_open_pending = False

    ui_initialization_pending = not (
        command_ready and toolbar_ready and palette_ready
    )
    if ui_initialization_pending:
        _log(
            'UI initialization remains pending after {} '
            '(command={}, toolbar={}, palette={}).'.format(
                trigger, command_ready, toolbar_ready, palette_ready
            )
        )
    else:
        _log('UI initialization completed after {}.'.format(trigger))
    return not ui_initialization_pending


def _show_palette():
    global initial_palette_open_pending
    if not _ensure_palette_created():
        return False
    shown = _set_palette_visible(True)
    if shown:
        initial_palette_open_pending = False
    return shown


def _toggle_palette():
    global initial_palette_open_pending
    palette = UI.palettes.itemById(PALETTE_ID)
    if palette and palette.isVisible:
        hidden = _set_palette_visible(False)
        if hidden:
            initial_palette_open_pending = False
        return hidden
    return _show_palette()


class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            if not _toggle_palette():
                raise RuntimeError('Fusion could not change the palette visibility.')
        except Exception:
            UI.messageBox(
                'Unable to show or hide Floating Parameters:\n\n' +
                traceback.format_exc()
            )


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        execute_handler = CommandExecuteHandler()
        args.command.execute.add(execute_handler)
        handlers.append(execute_handler)


def run(context):
    global active_selection_handler, bloodhound_enabled, document_activated_handler
    global initial_palette_open_pending, ui_initialization_pending
    global workspace_activated_handler
    try:
        is_application_startup = bool(
            context.get('IsApplicationStartup', False)
        ) if isinstance(context, dict) else False
        _log('run called; IsApplicationStartup={}.'.format(is_application_startup))

        bloodhound_enabled = False
        ui_initialization_pending = True
        initial_palette_open_pending = True

        if not document_activated_handler:
            document_activated_handler = DocumentActivatedHandler()
            APP.documentActivated.add(document_activated_handler)
            handlers.append(document_activated_handler)
        if not active_selection_handler:
            active_selection_handler = ActiveSelectionChangedHandler()
            UI.activeSelectionChanged.add(active_selection_handler)
            handlers.append(active_selection_handler)

        if not workspace_activated_handler:
            workspace_activated_handler = WorkspaceActivatedHandler()
            UI.workspaceActivated.add(workspace_activated_handler)
            handlers.append(workspace_activated_handler)

        if not is_application_startup:
            _ensure_ui_initialized('manual run')
        else:
            _log('Deferring UI initialization until Fusion activates a workspace or document.')
    except Exception:
        UI.messageBox('Floating Parameters failed to start:\n\n' + traceback.format_exc())


def stop(context):
    global active_selection_handler, bloodhound_enabled, command_created_handler
    global document_activated_handler, initial_palette_open_pending
    global ui_initialization_pending, workspace_activated_handler
    try:
        bloodhound_enabled = False
        ui_initialization_pending = False
        initial_palette_open_pending = False
        if active_selection_handler:
            UI.activeSelectionChanged.remove(active_selection_handler)
            active_selection_handler = None

        if document_activated_handler:
            APP.documentActivated.remove(document_activated_handler)
            document_activated_handler = None

        if workspace_activated_handler:
            UI.workspaceActivated.remove(workspace_activated_handler)
            workspace_activated_handler = None

        palette = UI.palettes.itemById(PALETTE_ID)
        if palette:
            palette.deleteMe()

        panel = UI.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        if panel:
            control = panel.controls.itemById(COMMAND_ID)
            if control:
                control.deleteMe()

        command_definition = UI.commandDefinitions.itemById(COMMAND_ID)
        if command_definition:
            command_definition.deleteMe()
    except Exception:
        UI.messageBox('Floating Parameters failed to stop cleanly:\n\n' + traceback.format_exc())
    finally:
        command_created_handler = None
        handlers.clear()
