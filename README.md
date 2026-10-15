# Workflow Config Editor

Keyboard accessible Windows editor for Codex, OpenCode, and CommandCode workflow settings. It resolves the current Windows user's profile at runtime, so the same EXE works for any user without embedding a developer account path.

Run `Start-WorkflowConfigEditor.ps1`, or open `dist\WorkflowConfigEditor.exe` directly.

The window keeps a simple list-detail editor visible: choose a configuration, choose one of 19 workflow categories, search for a setting, then edit its value. `Start guided change` announces four questions: configuration, category, setting, and value. Booleans use checkboxes; known choices use radio buttons; free-form values use a text editor. `Review change`, `Save change`, `Make another change`, `Undo last change`, `Backups`, and `Reload` are available. Review shows the configuration, setting, current value, and pending value before saving. The current and pending values are shown together. After saving, the backup path and sync result are announced. Undo asks for confirmation, checks that the file was not changed externally, and restores the exact backup from that save. `Backups` lists valid backups newest first and restores a selected backup after confirmation, creating a recovery backup first. Every save checks for an external change, writes a timestamped backup, and keeps the five newest backups. Canonical agent instructions and taste files are synchronized through the existing shared scripts after saving.

For NVDA, use `Tab` or `F6` to move between the configuration, category, settings, and editor panes. Use `Ctrl+F` to jump to and select the settings search, arrow keys in lists, `Enter` to select a setting, and `Escape` to clear a search with no matches. `Ctrl+R` reviews the pending change; `Ctrl+S` saves it. Press `F1` or activate `Help (F1)` whenever you get stuck; focus returns to the control you were using when the instructions close.

The repeatable spoken-output check is in [`docs/ACCESSIBILITY-CHECKLIST.md`](docs/ACCESSIBILITY-CHECKLIST.md).

Build or refresh the executable:

```powershell
python -m pip install --user -r requirements.txt
npm install --ignore-scripts
Copy-Item "$env:LOCALAPPDATA\BlindPilot\runtimes\node\node-v24.21.0-win-x64\node.exe" .\node.exe
python -m PyInstaller --noconfirm --clean workflow_config_editor.spec
```

The bundled executable includes the Node runtime and JSONC parser needed for format-preserving JSONC edits.
