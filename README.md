# Workflow Config Editor

Keyboard accessible Windows editor for Codex, OpenCode, and CommandCode workflow settings. It resolves the current Windows user's profile at runtime, so the same EXE works for any user without embedding a developer account path.

Run `Start-WorkflowConfigEditor.ps1`, or open `dist\WorkflowConfigEditor.exe` directly.

The window keeps a simple list-detail editor visible: choose a configuration, choose one of 19 workflow categories, search for a setting, then edit its value. All 19 categories remain visible with counts, including empty categories, so users can see the full workflow map. `Start guided change` opens a four-question keyboard wizard for configuration, category, setting, and value; guided progress appears while that flow is active. Booleans use checkboxes; known choices use radio buttons; free-form values use a text editor. `Review change`, `Save change`, `Make another change`, `Undo last change`, `Backups`, and `Reload` are available. Review shows the configuration, setting, current value, and pending value before saving. The current and pending values are shown together. After saving, the backup path and sync result are announced. Undo asks for confirmation, checks that the file was not changed externally, and restores the exact backup from that save. `Backups` lists valid backups newest first and restores a selected backup after confirmation, creating a recovery backup first. Every save checks for an external change, writes a timestamped backup, and keeps the five newest backups. Canonical agent instructions and taste files are synchronized through the existing shared scripts after saving.

For a first change, activate `Start guided change` or press `Ctrl+G`. Each question opens a choice dialog; select an answer and press `Enter` to continue: configuration, category, and setting. The wizard then closes and focuses the value control in the right pane. Press `Ctrl+R` to review, then choose Yes to save.

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
