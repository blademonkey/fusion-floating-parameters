# Floating Parameters — Release Notes

Floating Parameters is an Autodesk Fusion add-in for viewing and editing user
parameters from a persistent, resizable palette.

These notes are arranged newest first. Each version section can be copied into
the description for its corresponding GitHub Release.

## v1.5.5: Faster access and clearer highlighting

This update makes the most common parameter workflow faster, improves
Bloodhound visibility, and makes the palette toggle available from both
Utilities and Solid.

### Added

- Added a second Floating Parameters toolbar control to the Solid Modify panel.
- Added a remembered QuickSave preference using the palette's existing local
  browser storage.
- Added an accessible Bloodhound match label to highlighted parameter names.

### Changed

- QuickSave is enabled by default when no saved preference exists.
- Bloodhound now highlights the complete parameter-name cell instead of showing
  only a narrow marker at the beginning of the row.
- Bloodhound highlighting preserves pending-change backgrounds and remains the
  same for numeric and text parameters.

### Reliability

- The Solid toolbar control is optional and never participates in the main
  startup-readiness gate.
- Missing Solid UI is retried on later workspace or document activation without
  delaying the palette or reopening a palette the user deliberately hid.
- Both toolbar controls are removed explicitly when the add-in stops.

## v1.5.4: Reliable startup and palette toggle

This patch waits for Fusion's interface to become ready before creating the
Floating Parameters toolbar control and palette during automatic startup.

### Added

- Added a custom Floating Parameters toolbar icon.
- The toolbar icon now toggles the existing palette between shown and hidden.
- Added startup diagnostics for command, toolbar, and palette readiness.

### Fixed

- The palette no longer relies on Fusion's workspace being ready during the
  initial add-in `run()` call.
- Missing toolbar or palette components are retried on later workspace and
  document activation events.
- Startup retries no longer reopen a palette after the user closes or hides it.
- Command, toolbar, palette, and handler creation are idempotent, preventing
  duplicate UI controls during a retry.

### Behavior

- **Run on Startup** continues to control whether Fusion loads the add-in.
- The toolbar icon controls only the palette's current visibility; it does not
  unload or disable the add-in.
- Closing or hiding the palette keeps it hidden for the current Fusion session.
  The palette opens again the next time the add-in starts.
- Bloodhound is disabled whenever the palette is hidden.
- Hiding uses Fusion's existing palette object rather than deleting and
  recreating it.

## v1.5.3 — Text parameter compatibility

This patch allows Floating Parameters to coexist with add-ins and designs that
create text user parameters, including version-number parameters.

### Added

- Text user parameters now appear in the palette as read-only values.
- Text values can be found using the existing parameter search.
- Read-only rows include a small type indicator.

### Fixed

- Opening a design containing a text parameter no longer causes Floating
  Parameters to request a numeric value and fail during startup.
- Each user parameter is read independently, so an unsupported or inaccessible
  parameter cannot prevent the remaining parameters from loading.
- Unsupported parameter types are displayed safely instead of being treated as
  numeric parameters.

### Behavior

- Numeric expression editing, batch Apply, QuickSave, rename, and Bloodhound
  continue to work as before.
- Text parameters are intentionally read-only in this release. Writable text
  support will require separate live Fusion round-trip testing.

## v1.5.2 — Blademonkey publishing identity

This release prepares Floating Parameters for publication under the
**blademonkey** GitHub identity.

### Changed

- Changed the manifest author to `blademonkey`.
- Licensed the source under the PolyForm Shield License 1.0.0.
- Replaced personal-name palette and command identifiers with identifiers in the
  `blademonkey` namespace.
- Removed the previous personal name from the distributable source.

### Upgrade note

Because the internal palette and command identifiers changed, stop the previous
version of the add-in before replacing its folder. Restart Fusion after installing
this release so it does not retain controls created by an earlier version.

## v1.5.1 — QuickSave data-loss protection

This patch protects pending work when QuickSave cannot reach an active Fusion
design.

### Fixed

- QuickSave no longer treats a response without refreshed design data as a
  successful save.
- The typed expression remains pending if the active design is unavailable.
- The affected row now displays the QuickSave failure instead of silently
  reverting to its previous expression.
- Unrelated pending edits remain untouched.

## v1.5.0 — QuickSave

This release adds an optional workflow for applying one parameter at a time.

### Added

- Added an opt-in **QuickSave** toggle beside the Apply controls.
- When QuickSave is enabled, pressing **Enter** applies only the expression in
  the active row.
- Added a dedicated single-parameter request and response path so saving one row
  does not clear other pending edits.
- Restores focus to the affected expression after Fusion responds.

### Behavior

- QuickSave defaults to off whenever the palette reloads.
- **Ctrl+Enter** on Windows and **Command+Enter** on macOS continue to apply the
  complete pending batch.
- Rejected expressions remain editable and display their error beside the row.
- The Apply button is temporarily disabled while a QuickSave request is in
  progress, preventing overlapping saves.

## v1.4.1 — Bloodhound rename correction

### Fixed

- Bloodhound highlighting now follows a user parameter immediately after that
  parameter is renamed.
- The highlighted-name set is remapped before the refreshed parameter table is
  rendered, so the accent no longer disappears until the next Fusion selection
  event.

## v1.4.0 — Compact Fusion-integrated layout and parameter renaming

This release reduces unnecessary interface chrome and adds safe, inline user
parameter renaming.

### Added

- Rename a user parameter by double-clicking its name.
- Keyboard users can focus a parameter name and press **Enter** or **F2** to
  begin renaming.
- Press **Enter** to submit a rename or **Escape** to cancel it.
- Parameter-name collisions are checked across all Fusion parameters before the
  rename is attempted.
- Fusion remains the authority for validating supported parameter names.
- Failed renames preserve the attempted name so it can be corrected in place.

### Changed

- Removed the redundant visible **Parameters** heading.
- Added a compact active-document row containing the document name, **+ New**,
  and Refresh controls.
- Kept the document row and search toolbar separate so controls remain usable at
  narrow palette widths.
- Adopted a flat, Fusion-matched surface treatment. True viewport transparency
  is not exposed by Fusion's documented palette API.
- Kept **+ New** as a text label for discoverability while retaining a compact
  footprint.

### Fixed

- Rename cancellation uses a genuine outside click instead of `blur`, avoiding
  a table-render re-entry crash.
- Background table renders no longer cancel an in-progress rename.
- Long active-document names now have a synchronized full-name tooltip.
- Narrow palettes no longer force controls beyond the viewport.
- The full visible width of each column divider is draggable.

### Safety behavior

- Renaming is blocked while any expression edits are pending. Apply or revert
  those edits before renaming a parameter.
- Fusion recalculates the design after a successful rename, and recompute
  failures are surfaced to the user.

## v1.3.1 — Compact parameter table

This release increases the number of parameters visible without sacrificing the
readability of editable expressions.

### Changed

- Reduced ordinary row height to approximately 33 pixels in the embedded browser.
- Increased the default parameter-name column width with a 40/38/22 split for
  Parameter, Expression, and Value.
- Kept names and calculated values on one line with ellipsis and full-value
  tooltips.
- Right-aligned the Value heading and calculated values.
- Retained the normal text size in editable expression fields.

### Fixed

- Long calculated values no longer create horizontal table scrolling.

## v1.3.0 — Bloodhound selection highlighting

This release introduces **Bloodhound**, an opt-in way to identify user
parameters that directly control selected Fusion dimensions and features.

### Added

- Added the Bloodhound toggle to the floating palette.
- Bloodhound evaluates the current Fusion selection immediately when enabled.
- Sketch dimensions resolve through their associated model parameter.
- Selected Fusion features resolve through model parameters created by that
  feature.
- Direct user-parameter dependencies are obtained from Fusion's parameter
  dependency graph without parsing expression text.
- Multiple supported selections highlight the union of their direct user
  parameters.
- Timeline selections are unwrapped when Fusion exposes the underlying object.

### Behavior

- Bloodhound defaults to off after every add-in start or palette reload.
- Unsupported selections are ignored rather than guessed.
- Clearing the Fusion selection clears Bloodhound highlights.
- Bloodhound does not modify, apply, revert, or discard expression edits.
- Highlights survive table re-renders and coexist with changed and error states.
- Bloodhound remains enabled while switching documents during the same palette
  session, but stale highlights and object references are cleared.

## v1.2.1 — Safer document switching and column resizing

### Changed

- New parameter names are checked against both user parameters and generated
  model parameters.
- Column widths remain percentage-based after dragging, preserving their
  proportions when the palette is resized.
- User-selected column proportions are remembered in local browser storage.

### Fixed

- Switching Fusion documents no longer discards pending edits without notice;
  the palette reports how many unsaved changes were discarded.
- Eliminated mixed pixel and percentage widths after a column resize.

## v1.2.0 — Parameter creation and resizable columns

### Added

- Create a user parameter directly from the floating palette.
- The creation form supports a name, expression, units, and optional comment.
- New parameters default to the active design's length units.
- Drag the table-header dividers to resize the Parameter, Expression, and Value
  columns.
- Added a per-row revert button for backing out of one pending expression edit.

### Safety behavior

- Parameter creation is blocked while expression edits are pending, preventing
  those edits from being lost during the resulting parameter refresh.
- Duplicate user-parameter names receive a friendly validation message.

## v1.1.0 — Editing safeguards and automatic refresh

### Added

- The palette refreshes automatically when the active Fusion document changes.
- Search now displays a clear message when no parameters match the query.
- Each changed row includes a revert control for restoring its original
  expression without affecting other edits.

### Fixed

- Manual Refresh now asks for confirmation before discarding pending edits.
- Design recompute exceptions and unsuccessful `computeAll()` results are shown
  to the user instead of being reported as successful updates.

## v1.0.1 — Windows palette URL correction

### Fixed

- Converted the local palette HTML path to a valid `file:///` URI before giving
  it to Fusion.
- Prevented Windows backslashes from being encoded as `%5C`, which previously
  caused the embedded browser to display `ERR_INVALID_URL` instead of loading
  the palette.

## v1.0.0 — Initial release

The first working release of Floating Parameters.

### Added

- Persistent Autodesk Fusion palette for user parameters.
- View parameter names, expressions, calculated values, units, and comments.
- Edit multiple user-parameter expressions from the palette.
- Apply pending expression changes as a batch.
- Filter parameters by name, expression, or comment.
- Display Fusion expression errors beside the affected row.
- Float or dock the palette in the Fusion interface.
- Automatically open the palette when the add-in starts.

## Installation

1. Download the ZIP attached to the desired GitHub Release.
2. Extract it so the resulting folder is named `FloatingParameters`.
3. Copy that folder to Fusion's per-user add-in directory:
   - Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`
   - macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
4. Open Fusion and select **Utilities > Add-Ins > Scripts and Add-Ins**.
5. Select **FloatingParameters** on the Add-Ins tab and run it.
6. Enable **Run on Startup** if it is not already enabled.

When upgrading, stop the running add-in, replace the complete
`FloatingParameters` folder, and restart Fusion. Avoid nesting one
`FloatingParameters` folder inside another.
