const state = {
  parameters: [],
  originals: new Map(),
  edits: new Map(),
  errors: {},
  defaultUnits: '',
  bloodhoundEnabled: false,
  bloodhoundDirect: new Set(),
  quickSaveEnabled: false,
  quickSaving: null,
  rename: null
};

const rows = document.getElementById('parameterRows');
const tableWrap = document.getElementById('tableWrap');
const message = document.getElementById('message');
const searchInput = document.getElementById('searchInput');
const count = document.getElementById('count');
const status = document.getElementById('status');
const applyButton = document.getElementById('applyButton');
const createOverlay = document.getElementById('createOverlay');
const createForm = document.getElementById('createForm');
const createError = document.getElementById('createError');
const createParameterButton = document.getElementById('createParameterButton');
const bloodhoundToggle = document.getElementById('bloodhoundToggle');
const quickSaveToggle = document.getElementById('quickSaveToggle');
const COLUMN_WIDTHS_KEY = 'floatingParameters.columnWidths.v1';

function send(action, data = {}) {
  if (window.adsk && adsk.fusionSendData) {
    adsk.fusionSendData(action, JSON.stringify(data));
  } else {
    setStatus('This page must be opened inside Fusion.', true);
  }
}

function setStatus(text, isError = false) {
  status.textContent = text || '';
  status.classList.toggle('error', isError);
}

function setDocumentName(name) {
  const documentName = document.getElementById('documentName');
  const text = name || 'No active design';
  documentName.textContent = text;
  documentName.title = text;
}

function removeRenameOutsideListener() {
  if (state.rename && state.rename.outsideHandler) {
    document.removeEventListener('mousedown', state.rename.outsideHandler, true);
    state.rename.outsideHandler = null;
  }
}

function cancelRename({renderTable = true} = {}) {
  if (!state.rename) return;
  removeRenameOutsideListener();
  state.rename = null;
  if (renderTable) render();
}

function submitRename() {
  if (!state.rename || state.rename.submitting) return;
  const newName = state.rename.attemptedName.trim();
  if (!newName || newName === state.rename.originalName) {
    cancelRename();
    return;
  }
  state.rename.attemptedName = newName;
  state.rename.error = '';
  state.rename.submitting = true;
  removeRenameOutsideListener();
  setStatus('Renaming…');
  send('rename', {
    oldName: state.rename.originalName,
    newName
  });
  render();
}

function startRename(parameter) {
  if (state.edits.size > 0) {
    window.alert('Apply or revert your pending edits before renaming a parameter.');
    return;
  }
  if (state.rename && state.rename.originalName === parameter.name) return;
  cancelRename({renderTable: false});
  const outsideHandler = event => {
    if (!event.target.closest('[data-rename-editor]')) cancelRename();
  };
  state.rename = {
    originalName: parameter.name,
    attemptedName: parameter.name,
    error: '',
    submitting: false,
    outsideHandler
  };
  document.addEventListener('mousedown', outsideHandler, true);
  render();
  const renameInput = rows.querySelector('.rename-input');
  if (renameInput) {
    renameInput.focus();
    renameInput.select();
  }
}

function currentExpression(parameter) {
  return state.edits.has(parameter.name)
    ? state.edits.get(parameter.name)
    : parameter.expression;
}

function render() {
  const activeRenameInput = document.activeElement &&
    document.activeElement.classList.contains('rename-input')
    ? document.activeElement
    : null;
  const renameSelection = activeRenameInput
    ? [activeRenameInput.selectionStart, activeRenameInput.selectionEnd]
    : null;
  const query = searchInput.value.trim().toLowerCase();
  const filtered = state.parameters.filter(parameter =>
    parameter.name.toLowerCase().includes(query) ||
    parameter.expression.toLowerCase().includes(query) ||
    (parameter.comment || '').toLowerCase().includes(query)
  );

  rows.replaceChildren();
  filtered.forEach(parameter => {
    const row = document.createElement('tr');
    row.dataset.name = parameter.name;
    row.classList.toggle('changed', state.edits.has(parameter.name));
    row.classList.toggle('error', Boolean(state.errors[parameter.name]));
    row.classList.toggle(
      'bloodhound-direct',
      state.bloodhoundDirect.has(parameter.name)
    );

    const nameCell = document.createElement('td');
    const isRenaming = state.rename && state.rename.originalName === parameter.name;
    if (isRenaming) {
      const renameInput = document.createElement('input');
      renameInput.className = 'rename-input';
      renameInput.dataset.renameEditor = '';
      renameInput.value = state.rename.attemptedName;
      renameInput.disabled = state.rename.submitting;
      renameInput.setAttribute('aria-label', `Rename ${parameter.name}`);
      renameInput.addEventListener('input', () => {
        if (state.rename) state.rename.attemptedName = renameInput.value;
      });
      renameInput.addEventListener('keydown', event => {
        if (event.key === 'Enter') {
          event.preventDefault();
          submitRename();
        } else if (event.key === 'Escape') {
          event.preventDefault();
          cancelRename();
        }
      });
      nameCell.appendChild(renameInput);
      if (state.rename.error) {
        const renameError = document.createElement('div');
        renameError.className = 'rename-error';
        renameError.textContent = state.rename.error;
        nameCell.appendChild(renameError);
      }
    } else {
      const name = document.createElement('div');
      name.className = 'name';
      name.tabIndex = 0;
      name.textContent = parameter.name;
      name.title = `${parameter.name} — double-click to rename`;
      name.addEventListener('dblclick', () => startRename(parameter));
      name.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === 'F2') {
          event.preventDefault();
          startRename(parameter);
        }
      });
      nameCell.appendChild(name);
    }
    if (!isRenaming && parameter.comment) {
      const comment = document.createElement('div');
      comment.className = 'comment';
      comment.textContent = parameter.comment;
      nameCell.appendChild(comment);
    }

    const expressionCell = document.createElement('td');
    const editor = document.createElement('div');
    editor.className = 'expression-editor';
    const input = document.createElement('input');
    input.className = 'expression';
    input.value = currentExpression(parameter);
    input.disabled = state.quickSaving === parameter.name;
    input.setAttribute('aria-label', `${parameter.name} expression`);
    const revertButton = document.createElement('button');
    revertButton.type = 'button';
    revertButton.className = 'revert-button';
    revertButton.textContent = '↶';
    revertButton.title = `Revert ${parameter.name}`;
    revertButton.setAttribute('aria-label', `Revert ${parameter.name}`);

    const syncRowEdit = () => {
      const original = state.originals.get(parameter.name);
      if (input.value === original) state.edits.delete(parameter.name);
      else state.edits.set(parameter.name, input.value);
      delete state.errors[parameter.name];
      updateDirtyState();
      const changed = state.edits.has(parameter.name);
      row.classList.toggle('changed', changed);
      revertButton.hidden = !changed;
      row.classList.remove('error');
      const existingError = row.querySelector('.row-error');
      if (existingError) existingError.remove();
    };

    input.addEventListener('input', syncRowEdit);
    input.addEventListener('keydown', event => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        applyChanges();
      } else if (event.key === 'Enter' && state.quickSaveEnabled) {
        event.preventDefault();
        applyOne(parameter.name);
      }
    });
    revertButton.addEventListener('click', () => {
      input.value = state.originals.get(parameter.name);
      syncRowEdit();
      input.focus();
    });
    revertButton.hidden = !state.edits.has(parameter.name);
    editor.append(input, revertButton);
    expressionCell.appendChild(editor);
    if (state.errors[parameter.name]) {
      const error = document.createElement('div');
      error.className = 'row-error';
      error.textContent = state.errors[parameter.name];
      expressionCell.appendChild(error);
    }

    const valueCell = document.createElement('td');
    valueCell.className = 'value';
    valueCell.textContent = parameter.valueText || String(parameter.value);
    valueCell.title = valueCell.textContent;

    row.append(nameCell, expressionCell, valueCell);
    rows.appendChild(row);
  });

  count.textContent = query
    ? `${filtered.length} of ${state.parameters.length}`
    : `${state.parameters.length}`;
  if (state.parameters.length === 0) {
    tableWrap.hidden = true;
    message.hidden = false;
    message.textContent = message.textContent || 'No user parameters.';
  } else if (filtered.length === 0) {
    tableWrap.hidden = true;
    message.hidden = false;
    message.textContent = `No parameters match "${searchInput.value.trim()}".`;
  } else {
    tableWrap.hidden = false;
    message.hidden = true;
  }
  updateDirtyState();
  if (renameSelection && state.rename) {
    const replacement = rows.querySelector('.rename-input');
    if (replacement && !replacement.disabled) {
      replacement.focus();
      replacement.setSelectionRange(renameSelection[0], renameSelection[1]);
    }
  }
}

function loadParameters(payload, {skipConfirm = false} = {}) {
  if (!skipConfirm && state.edits.size > 0) {
    const proceed = window.confirm(
      `You have ${state.edits.size} unsaved change${state.edits.size === 1 ? '' : 's'}. ` +
      'Refreshing will discard them. Continue?'
    );
    if (!proceed) return;
  }

  const discardedEdits = payload.source === 'document' ? state.edits.size : 0;
  if (payload.source === 'document') state.bloodhoundDirect.clear();
  state.parameters = payload.parameters || [];
  state.originals = new Map(state.parameters.map(p => [p.name, p.expression]));
  state.edits.clear();
  state.errors = {};
  state.defaultUnits = payload.defaultUnits || '';
  cancelRename({renderTable: false});
  setDocumentName(payload.document);
  message.textContent = payload.message || '';
  setStatus(payload.ok ? '' : payload.message, !payload.ok);
  render();
  if (discardedEdits > 0) {
    setStatus(
      `Switched documents — ${discardedEdits} unsaved change${discardedEdits === 1 ? '' : 's'} ` +
      `${discardedEdits === 1 ? 'was' : 'were'} discarded.`
    );
  }
}

function openCreateForm() {
  if (state.edits.size > 0) {
    window.alert('Apply or revert your pending edits before creating a parameter.');
    return;
  }
  if (!state.defaultUnits && document.getElementById('documentName').textContent === 'No active design') {
    setStatus('Open a Fusion design before creating a parameter.', true);
    return;
  }
  createForm.reset();
  document.getElementById('newUnits').value = state.defaultUnits;
  createError.textContent = '';
  createOverlay.hidden = false;
  document.getElementById('newName').focus();
}

function closeCreateForm() {
  createOverlay.hidden = true;
  createParameterButton.disabled = false;
}

function initializeColumnResize() {
  const columns = [
    document.getElementById('nameColumn'),
    document.getElementById('expressionColumn'),
    document.getElementById('valueColumn')
  ];
  const minimumWidth = 72;

  try {
    const savedWidths = JSON.parse(localStorage.getItem(COLUMN_WIDTHS_KEY));
    if (
      Array.isArray(savedWidths) &&
      savedWidths.length === columns.length &&
      savedWidths.every(width => Number.isFinite(width) && width > 0)
    ) {
      const total = savedWidths.reduce((sum, width) => sum + width, 0);
      savedWidths.forEach((width, index) => {
        columns[index].style.width = `${(width / total) * 100}%`;
      });
    }
  } catch (error) {
    // Storage can be unavailable in some embedded-browser configurations.
  }

  document.querySelectorAll('.resize-handle').forEach(handle => {
    handle.addEventListener('mousedown', event => {
      event.preventDefault();
      const divider = Number(handle.dataset.divider);
      const startX = event.clientX;
      const tableWidth = document.querySelector('table').getBoundingClientRect().width;
      const startingWidths = columns.map(column => column.getBoundingClientRect().width);
      const leftWidth = startingWidths[divider];
      const rightWidth = startingWidths[divider + 1];
      let currentPercentages = startingWidths.map(width => (width / tableWidth) * 100);

      document.body.classList.add('resizing-columns');
      const move = moveEvent => {
        const delta = Math.max(
          minimumWidth - leftWidth,
          Math.min(moveEvent.clientX - startX, rightWidth - minimumWidth)
        );
        const widths = [...startingWidths];
        widths[divider] = leftWidth + delta;
        widths[divider + 1] = rightWidth - delta;
        currentPercentages = widths.map(width => (width / tableWidth) * 100);
        columns.forEach((column, index) => {
          column.style.width = `${currentPercentages[index]}%`;
        });
      };
      const stop = () => {
        document.body.classList.remove('resizing-columns');
        document.removeEventListener('mousemove', move);
        document.removeEventListener('mouseup', stop);
        try {
          localStorage.setItem(COLUMN_WIDTHS_KEY, JSON.stringify(currentPercentages));
        } catch (error) {
          // Column resizing still works when persistence is unavailable.
        }
      };
      document.addEventListener('mousemove', move);
      document.addEventListener('mouseup', stop);
    });
  });
}

function updateDirtyState() {
  const dirty = state.edits.size;
  applyButton.disabled = dirty === 0 || state.quickSaving !== null;
  if (dirty) setStatus(`${dirty} unsaved change${dirty === 1 ? '' : 's'}`);
}

function applyChanges() {
  if (!state.edits.size || state.quickSaving !== null) return;
  applyButton.disabled = true;
  setStatus('Applying…');
  send('apply', {
    updates: [...state.edits].map(([name, expression]) => ({name, expression}))
  });
}

function applyOne(name) {
  if (!state.quickSaveEnabled || state.quickSaving !== null) return;
  if (!state.edits.has(name)) {
    setStatus(`No unsaved change for ${name}.`);
    return;
  }

  state.quickSaving = name;
  setStatus(`Saving ${name}…`);
  render();
  send('applyOne', {
    update: {name, expression: state.edits.get(name)}
  });
}

function focusExpression(name) {
  const row = [...rows.querySelectorAll('tr')].find(item => item.dataset.name === name);
  const expression = row ? row.querySelector('.expression') : null;
  if (expression && !expression.disabled) {
    expression.focus();
    expression.select();
  }
}

window.fusionJavaScriptHandler = {
  handle(action, rawData) {
    try {
      const payload = rawData ? JSON.parse(rawData) : {};
      if (action === 'parameters') {
        loadParameters(payload, {skipConfirm: payload.source !== 'manual'});
      } else if (action === 'applyResult') {
        state.errors = payload.errors || {};
        if (payload.data) {
          const failedEdits = new Map(
            [...state.edits].filter(([name]) => state.errors[name])
          );
          state.parameters = payload.data.parameters || [];
          state.originals = new Map(state.parameters.map(p => [p.name, p.expression]));
          state.edits = failedEdits;
          setDocumentName(payload.data.document);
        }
        setStatus(payload.message, !payload.ok);
        render();
      } else if (action === 'applyOneResult') {
        const parameterName = payload.name || state.quickSaving;
        const retainedEdits = new Map(state.edits);
        state.errors = {...state.errors};
        delete state.errors[parameterName];
        if (payload.errors && payload.errors[parameterName]) {
          state.errors[parameterName] = payload.errors[parameterName];
        } else if (payload.data) {
          retainedEdits.delete(parameterName);
        } else {
          state.errors[parameterName] = payload.message || 'QuickSave failed.';
        }
        if (payload.data) {
          state.parameters = payload.data.parameters || [];
          state.originals = new Map(state.parameters.map(p => [p.name, p.expression]));
          setDocumentName(payload.data.document);
        }
        state.edits = retainedEdits;
        state.quickSaving = null;
        setStatus(payload.message, !payload.ok);
        render();
        focusExpression(parameterName);
      } else if (action === 'createResult') {
        createParameterButton.disabled = false;
        if (payload.created && payload.data) {
          loadParameters(payload.data, {skipConfirm: true});
          closeCreateForm();
          setStatus(payload.message, !payload.ok);
        } else {
          createError.textContent = payload.message || 'Fusion rejected the new parameter.';
        }
      } else if (action === 'renameResult') {
        if (payload.renamed && payload.data) {
          if (
            payload.oldName &&
            payload.newName &&
            state.bloodhoundDirect.has(payload.oldName)
          ) {
            state.bloodhoundDirect.delete(payload.oldName);
            state.bloodhoundDirect.add(payload.newName);
          }
          cancelRename({renderTable: false});
          loadParameters(payload.data, {skipConfirm: true});
          setStatus(payload.message, !payload.ok);
        } else if (payload.unchanged) {
          cancelRename();
          setStatus(payload.message, false);
        } else if (state.rename) {
          state.rename.submitting = false;
          state.rename.error = payload.message || 'Fusion rejected the new parameter name.';
          const outsideHandler = event => {
            if (!event.target.closest('[data-rename-editor]')) cancelRename();
          };
          state.rename.outsideHandler = outsideHandler;
          document.addEventListener('mousedown', outsideHandler, true);
          setStatus(state.rename.error, true);
          render();
          const renameInput = rows.querySelector('.rename-input');
          if (renameInput) {
            renameInput.focus();
            renameInput.select();
          }
        }
      } else if (action === 'bloodhoundState') {
        state.bloodhoundEnabled = payload.enabled === true;
        bloodhoundToggle.checked = state.bloodhoundEnabled;
        if (!state.bloodhoundEnabled) state.bloodhoundDirect.clear();
        render();
      } else if (action === 'highlight') {
        if (state.bloodhoundEnabled) {
          state.bloodhoundDirect = new Set(payload.direct || []);
        } else {
          state.bloodhoundDirect.clear();
        }
        render();
      } else if (action === 'fatalError') {
        setStatus(payload.message || 'Unexpected add-in error.', true);
      }
      return 'OK';
    } catch (error) {
      setStatus(error.message, true);
      return error.message;
    }
  }
};

document.getElementById('refreshButton').addEventListener('click', () => send('refresh'));
bloodhoundToggle.addEventListener('change', () => {
  state.bloodhoundEnabled = bloodhoundToggle.checked;
  if (!state.bloodhoundEnabled) {
    state.bloodhoundDirect.clear();
    render();
  }
  send('setBloodhound', {enabled: state.bloodhoundEnabled});
});
quickSaveToggle.addEventListener('change', () => {
  state.quickSaveEnabled = quickSaveToggle.checked;
  setStatus(
    state.quickSaveEnabled
      ? 'QuickSave enabled — Enter saves the active parameter.'
      : 'QuickSave disabled.'
  );
});
document.getElementById('newParameterButton').addEventListener('click', openCreateForm);
document.getElementById('cancelCreateButton').addEventListener('click', closeCreateForm);
createOverlay.addEventListener('mousedown', event => {
  if (event.target === createOverlay) closeCreateForm();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !createOverlay.hidden) closeCreateForm();
});
createForm.addEventListener('submit', event => {
  event.preventDefault();
  createError.textContent = '';
  createParameterButton.disabled = true;
  send('create', {
    name: document.getElementById('newName').value,
    expression: document.getElementById('newExpression').value,
    units: document.getElementById('newUnits').value,
    comment: document.getElementById('newComment').value
  });
});
applyButton.addEventListener('click', applyChanges);
searchInput.addEventListener('input', render);
initializeColumnResize();
window.addEventListener('DOMContentLoaded', () => send('ready'));
