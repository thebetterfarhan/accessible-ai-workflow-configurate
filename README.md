# Workflow Config Editor

Keyboard accessible Windows editor for Codex, OpenCode, and CommandCode workflow settings. It resolves the current Windows user's profile at runtime, so the same EXE works for any user without embedding a developer account path.

Run `Start-WorkflowConfigEditor.ps1`, or open `dist\WorkflowConfigEditor.exe` directly.

The window is a five-question guided interview: choose a configuration, choose one of 19 workflow categories, choose a setting, choose or type the answer, then review the change before saving. Booleans use checkboxes; known choices use radio buttons; free-form values use a text editor. `Back`, `Next`, `Save this change`, `Make another change`, `Undo last change`, `Save`, and `Reload` are available. After saving, the backup path and sync result are announced. Undo asks for confirmation, checks that the file was not changed externally, and restores the exact backup from that save. Every save checks for an external change, writes a timestamped backup, and keeps the five newest backups. Canonical agent instructions and taste files are synchronized through the existing shared scripts after saving.

For NVDA, answer one question at a time. Use arrow keys to choose an answer, `Tab` to reach Next, and `Shift+Tab` to reach Back. Press `Enter` on the answer to continue. The final question presents the checkbox, radio buttons, or text value.

Build or refresh the executable:

```powershell
python -m pip install --user -r requirements.txt
npm install --ignore-scripts
Copy-Item "$env:LOCALAPPDATA\BlindPilot\runtimes\node\node-v24.21.0-win-x64\node.exe" .\node.exe
python -m PyInstaller --noconfirm --clean workflow_config_editor.spec
```

The bundled executable includes the Node runtime and JSONC parser needed for format-preserving JSONC edits.
