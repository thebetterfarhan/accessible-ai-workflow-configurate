# Workflow Config Editor

Keyboard accessible Windows editor for Codex, OpenCode, and CommandCode workflow settings. It resolves the current Windows user's profile at runtime, so the same EXE works for any user without embedding a developer account path.

Run `Start-WorkflowConfigEditor.ps1`, or open `dist\WorkflowConfigEditor.exe` directly.

The window keeps a simple list-detail editor visible: choose a configuration, choose a workflow category, search for a setting, then edit its value. The known 19 categories remain visible with counts, and declared categories from a configuration are added automatically. `Start guided change` opens a category-by-category wizard. Each category asks the needed questions with `Back`, `Next`, and `Skip category`; the final question checks the current and new value before saving. Guided progress announces the category and question number. Booleans use checkboxes; known choices use radio buttons; free-form values use a text editor. `Review change`, `Save change`, `Make another change`, `Undo last change`, `Backups`, and `Reload` are available. Review shows the configuration, setting, current value, and pending value before saving. The current and pending values are shown together. After saving, the backup path and sync result are announced. Undo asks for confirmation, checks that the file was not changed externally, and restores the exact backup from that save. `Backups` lists valid backups newest first and restores a selected backup after confirmation, creating a recovery backup first. Every save checks for an external change, writes a timestamped backup, and keeps the five newest backups. Canonical agent instructions and taste files are synchronized through the existing shared scripts after saving.

For a first change, activate `Start guided change` or press `Ctrl+G`. The wizard selects the first populated category, explains what that category controls, and explains the possible values for the selected setting. It then asks you to confirm the category, choose a setting, choose or enter its value, and check the change. Press `Next` to continue, `Back` to correct an answer, or `Skip category` to move on. Each completed category is reviewed and saved before the next category starts.

`Welcome` gives a short orientation. `Guidance: Detailed` can be toggled to `Guidance: Short` for less spoken text.

`Pause guided setup` keeps the current category and question in memory. The button changes to `Resume guided setup`; category labels show `Not started`, `In progress`, or `Done`.

`Next` validates the answer before moving on. Invalid JSON, numbers, or required values keep focus on the answer and explain the fix. Guided value controls also show an example.

`Change summary` lists the current and saved guided changes. `Reset category` restores the loaded value for the current pending answer without writing to disk.

`Presets` previews Beginner, Balanced, or Advanced values when matching settings exist; saving still requires review. `Recent changes` lists saved edits from this session. `Health check` reports loaded-file and editable-setting status without repairing anything automatically.

For NVDA, use `Tab` or `F6` to move between the configuration, category, settings, and editor panes. Use `Ctrl+F` to jump to and select the settings search, `Ctrl+G` to start guided mode, arrow keys in lists, `Enter` to select a setting, and `Escape` to clear a search with no matches. `Ctrl+R` reviews the pending change; `Ctrl+B` opens backup history; `Ctrl+S` saves it. Press `F1` or activate `Help (F1)` whenever you get stuck; focus returns to the control you were using when the instructions close.

The repeatable spoken-output check is in [`docs/ACCESSIBILITY-CHECKLIST.md`](docs/ACCESSIBILITY-CHECKLIST.md).

Build or refresh the executable:

```powershell
python -m pip install --user -r requirements.txt
npm install --ignore-scripts
Copy-Item "$env:LOCALAPPDATA\BlindPilot\runtimes\node\node-v24.21.0-win-x64\node.exe" .\node.exe
python -m PyInstaller --noconfirm --clean workflow_config_editor.spec
```

The bundled executable includes the Node runtime and JSONC parser needed for format-preserving JSONC edits.

Markdown instruction files are edited by section: choose a heading such as `Working style`, then replace the section body in the multiline editor. Generated `TASTE:` sections remain protected.

The editor labels this value as `Type: markdown section body` so new users know why the answer area is multiline.
