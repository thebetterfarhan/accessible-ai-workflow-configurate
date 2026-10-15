# Accessible AI Workflow Configurate

Keyboard accessible Windows editor for Codex, OpenCode, and CommandCode workflow settings. It resolves the current Windows user's profile at runtime, so the same EXE works for any user without embedding a developer account path.

Run `Start-WorkflowConfigEditor.ps1`, or open `dist\AccessibleAIWorkflowConfigurate.exe` directly.

The window keeps a simple list-detail editor visible: choose a configuration, choose a workflow category, search for a setting, then edit its value. The known 19 categories remain visible with counts, and declared categories from a configuration are added automatically. `Start guided change` opens a category-by-category wizard. Each category asks the needed questions with `Back`, `Next`, and `Skip category`; the final question checks the current and new value before saving. Guided progress announces the category and question number. Booleans use checkboxes; known choices use radio buttons; free-form values use a text editor. `Review change`, `Save change`, `Make another change`, `Undo last change`, `Backups`, and `Reload` are available. Review shows the configuration, setting, current value, and pending value before saving. The current and pending values are shown together. After saving, the backup path and sync result are announced. Undo asks for confirmation, checks that the file was not changed externally, and restores the exact backup from that save. `Backups` lists valid backups newest first and restores a selected backup after confirmation, creating a recovery backup first. Every save checks for an external change, writes a timestamped backup, and keeps the five newest backups. Canonical agent instructions and taste files are synchronized through the existing shared scripts after saving.

When you select a setting, `What this changes` explains its category in plain language before you edit the value.

For a first change, activate `Start guided change` or press `Ctrl+G`. The wizard selects the first populated category, explains what that category controls, and explains the possible values for the selected setting. It then asks you to confirm the category, choose a setting, choose or enter its value, and check the change. Press `Next` to continue, `Back` to correct an answer, or `Skip category` to move on. Each completed category is reviewed and saved before the next category starts.

`Welcome` gives a short orientation. `Guidance: Detailed` can be toggled to `Guidance: Short` for less spoken text.

`Pause guided setup` keeps the current category and question in memory. The button changes to `Resume guided setup`; category labels show `Not started`, `In progress`, or `Done`.

Guided mode also shows a short `Guided help` instruction for the current step: choose a category, choose a setting, enter an unsaved value, or review before saving.

`Next` validates the answer before moving on. Invalid JSON, numbers, or required values keep focus on the answer and explain the fix. Guided value controls also show an example.

`Change summary` lists the current and saved guided changes. `Reset category` restores the loaded value for the current pending answer without writing to disk.

`Presets` previews Beginner, Balanced, or Advanced values when matching settings exist; saving still requires review. `Recent changes` lists saved edits from this session. `Health check` reports loaded-file and editable-setting status without repairing anything automatically.

`Health check` also reports the total supported sources and editable settings across the workflow, including sources that are unavailable because their file format needs repair.

`All sources` shows every supported workflow source discovered for the current Windows user and the total editable setting count. Choose a source in that list to open it directly; the editor still opens one source at a time through the `Configuration` list. A count such as 140 means the selected `Main Codex settings` file, not the whole workflow. Authentication, runtime state, history, and cache files stay excluded.

For NVDA, use `Tab` or `F6` to move between the configuration, category, settings, and editor panes. Use `Ctrl+F` to jump to and select the settings search, `Ctrl+G` to start guided mode, arrow keys in lists, `Enter` to select a setting, and `Escape` to clear a search with no matches. `Ctrl+R` reviews the pending change; `Ctrl+B` opens backup history; `Ctrl+S` saves it. Press `F1` or activate `Help (F1)` whenever you get stuck; focus returns to the control you were using when the instructions close.

The repeatable spoken-output check is in [`docs/ACCESSIBILITY-CHECKLIST.md`](docs/ACCESSIBILITY-CHECKLIST.md).

The reproducible local release gate is in [`docs/RELEASE-CHECKLIST.md`](docs/RELEASE-CHECKLIST.md). It records automated checks, the NVDA gate, and the boundary between local release evidence and publishing.

The current evidence handoff is in [`docs/RELEASE-SIGNOFF.md`](docs/RELEASE-SIGNOFF.md).

Current local release notes are in [`docs/RELEASE-NOTES.md`](docs/RELEASE-NOTES.md).

Change history is in [`CHANGELOG.md`](CHANGELOG.md).

Third-party license notices for the bundled Node runtime and JSONC parser are in [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

## System requirements

- Windows 10 or Windows 11, 64-bit.
- No administrator access is required. The app is portable.
- NVDA is recommended for the spoken accessibility check.
- The app edits local Codex, OpenCode, and CommandCode workflow files. It does not need an internet connection to edit them.

## Install

1. Extract the local ZIP to a folder you control.
2. Open `AccessibleAIWorkflowConfigurate.exe`.
3. Use `Start guided change` for the first setup, or choose a source and category directly.

Do not run the EXE from inside the ZIP. Keep the EXE and its companion files together.

## Uninstall

Close the app, then delete the extracted application folder. The app does not install a service or scheduled task. It does not delete your workflow configuration files, backups, or changes; remove those separately only when you intend to.

## Privacy and support

The editor reads and writes local workflow files for the current Windows user. It does not upload configuration contents. The bundled Node runtime is used locally for JSONC parsing. Save and sync actions may invoke local scripts configured by the user.

When reporting a problem, include the app version or commit, Windows version, NVDA version if relevant, exact steps, the spoken or visible error, and the EXE or ZIP hash. Remove passwords, tokens, private paths, and workflow contents before sharing logs.

## Known limitations

- The app edits supported workflow settings only. Credentials, runtime state, history, and cache files are excluded.
- Unsupported or malformed sources are reported as unavailable and are not repaired automatically.
- The portable EXE is unsigned and has no automatic update service.
- Spoken labels and focus recovery still require a real NVDA check; automated tests cannot prove speech output.
- The source code is licensed under the MIT License. See [`LICENSE`](LICENSE). The portable EXE is still an unsigned local release candidate until publication is approved.

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
