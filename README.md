<img width="312" height="608" alt="image" src="https://github.com/user-attachments/assets/a495a1dc-07b6-4ade-82fa-af19e8dd5470" />


# Floating Parameters for Autodesk Fusion

Floating Parameters is a Fusion add-in that keeps user parameters available in
a persistent, resizable palette while you model.

## Features

- Edit user-parameter expressions without reopening **Change Parameters**.
- Create user parameters with a name, expression, units, and optional comment.
- Rename a user parameter by double-clicking its name, or focusing it and pressing
  **Enter** or **F2**.
- Enable **Bloodhound** to highlight parameters directly used by a selected
  sketch dimension or feature.
- Float the palette or dock it in the Fusion interface.
- See calculated values, units, and parameter comments.
- View Fusion text parameters safely as read-only values.
- Drag the column dividers to resize the parameter, expression, and value columns.
- Filter by name, expression, or comment.
- Make several edits and apply them as a batch.
- Enable **QuickSave** to apply only the active parameter by pressing **Enter**.
- See errors beside any expression Fusion rejects.
- Press **Ctrl+Enter** (Windows) or **Command+Enter** (macOS) while editing to apply.

This version intentionally displays **user parameters only**. Model parameters
are excluded because changing generated feature dimensions directly can be
confusing and much easier to break accidentally.

## License

Floating Parameters is source-available under the
[PolyForm Shield License 1.0.0](LICENSE.md). You may use and modify it for
permitted purposes, but you may not use it to provide a competing product,
whether paid or free. See the license file for the complete terms.

Required Notice: Copyright 2026 blademonkey

## Install on Windows

1. Extract the `FloatingParameters.zip` download.
2. Copy the resulting `FloatingParameters` folder to:
   `%APPDATA%\\Autodesk\\Autodesk Fusion 360\\API\\AddIns\\`
3. In Fusion, open **Utilities > Add-Ins > Scripts and Add-Ins**.
4. Select the **Add-Ins** tab, choose **FloatingParameters**, and click **Run**.
5. Enable **Run on Startup** if Fusion does not pick up the manifest setting automatically.

## Install on macOS

1. Extract the ZIP.
2. Copy the `FloatingParameters` folder to:
   `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
3. In Fusion, open **Utilities > Add-Ins > Scripts and Add-Ins**.
4. Select **FloatingParameters** and click **Run**.

The palette opens when the add-in starts. If you close it, use the
**Floating Parameters** button in the **Utilities > Add-Ins** toolbar panel.

## Usage

1. Open a parametric Fusion design containing at least one user parameter.
2. Change one or more expressions, such as `40 mm`, `LegWidth * 1.5`, or `2 in`.
3. Click **Apply changes**.
4. Use the circular-arrow button to refresh after parameters are added, removed,
   renamed, or changed elsewhere.

## Troubleshooting

- If the add-in does not appear, confirm the extracted structure is
  `API/AddIns/FloatingParameters/FloatingParameters.py` and not a nested duplicate folder.
- If Fusion reports a Python traceback, copy the complete message; it identifies
  the API call that needs adjustment for your Fusion build.
- If a parameter expression is invalid or creates a circular dependency, Fusion
  rejects it and the palette leaves that edit in place with an error message.

## Version

1.5.3

### 1.5.3

- Adds compatibility with Fusion text user parameters.
- Displays text parameters as read-only values without requesting numeric data.
- Isolates parameter-loading failures so one unsupported parameter cannot prevent
  the palette from opening.
- Preserves numeric editing, QuickSave, rename, search, and Bloodhound behavior.

### 1.5.2

- Publishes the add-in under the `blademonkey` author identity and removes the
  previous personal-name identifiers from the distributable source.

### 1.5.1

- Keeps the pending expression and shows a row-level error if QuickSave cannot
  reach an active Fusion design.

### 1.5.0

- Adds an opt-in QuickSave mode that applies only the active parameter when
  **Enter** is pressed.
- Keeps other pending expression edits intact while QuickSave applies one row.
- Keeps **Ctrl+Enter**/**Command+Enter** assigned to applying the full batch.

### 1.4.1

- Preserves an active Bloodhound highlight when its user parameter is renamed.

### 1.4.0

- Removes the redundant in-palette title and replaces it with a compact active-design row.
- Adds inline user-parameter renaming with collision checks and Fusion validation.
- Preserves an attempted name when Fusion rejects a rename.
- Uses a flat Fusion-matched panel treatment; transparent host windows are not exposed by Fusion.
- Prevents narrow palette widths from forcing the controls beyond the viewport.
- Keeps the active-document tooltip synchronized and improves column-divider hit areas.

### 1.3.1

- Compacts ordinary parameter rows to show more parameters in the same palette.
- Gives parameter names more space with a 40/38/22 default column split.
- Keeps long names and calculated values on one line with ellipsis and tooltips.
- Right-aligns calculated values while preserving full-size editable expressions.
- Prevents long calculated values from creating horizontal table scrolling.

### 1.3.0

- Adds the opt-in Bloodhound selection-highlighting feature.
- Resolves sketch dimensions and Fusion features through documented parameter
  dependencies without parsing expressions.
- Supports multiple selections and timeline-object unwrapping.
- Preserves Bloodhound highlights across table re-renders while keeping changed
  and error states visible.
- Keeps Bloodhound off by default after every add-in start or palette reload.

### 1.2.1

- Checks new parameter names against both user and model parameters.
- Keeps all resized columns percentage-based so palette resizing preserves their proportions.
- Remembers column proportions when the palette is reopened.
- Reports when switching documents discards pending edits.

### 1.2.0

- Adds user-parameter creation from the floating palette.
- Adds draggable column dividers for long names and expressions.
- Defaults new parameters to the active design's length units.
- Prevents creation while expression edits are pending, avoiding accidental loss.

### 1.1.0

- Protects pending edits from accidental manual refreshes.
- Refreshes automatically when the active Fusion document changes.
- Reports design recompute failures.
- Shows a clear empty state when a search has no matches.
- Adds a per-row revert button for pending edits.

### 1.0.1

- Fixed palette loading on Windows by converting the local HTML path to a valid
  `file:///C:/...` URI instead of allowing backslashes to be encoded as `%5C`.
