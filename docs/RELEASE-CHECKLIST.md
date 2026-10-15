# Accessible AI Workflow Configurate release checklist

Use this checklist before sharing a build. It verifies the local portable EXE and does not publish anything.

Do every section in order. Stop on the first failed check. A passing test suite alone is not a release approval.

## 0. Freeze the candidate

- Confirm the repository, branch, and intended version.
- Confirm `git status --short` shows only intended release changes.
- Read the diff. Check for secrets, personal paths, credentials, logs, databases, and debug files.
- Confirm the release boundary: local ZIP, private test, or a later published release.
- Do not publish, push, tag, sign, or deploy during this checklist.

## Automated gate

Run from the repository root:

```powershell
python -m pytest -q
python -m py_compile workflow_config_editor.py config_backend.py
node --check jsonc_bridge.cjs
npm audit --omit=dev --audit-level=high
python workflow_config_editor.py --smoke
python -m PyInstaller --noconfirm --clean workflow_config_editor.spec
dist\AccessibleAIWorkflowConfigurate.exe --smoke
```

Expected results:

- all tests pass
- no Python or Node syntax errors
- npm reports no high-severity vulnerabilities
- source and packaged smoke checks exit with code 0
- the launcher points to `dist\AccessibleAIWorkflowConfigurate.exe`
- the Git working tree is clean

Also start the packaged EXE normally once and inspect the startup output. Treat any warning, traceback, unhandled exception, invalid configuration message, or missing-file message as a failed gate. Close the app after this check.

If the app reads user or tool configuration, validate those files separately before release. A malformed optional file must be reported clearly and remain unchanged; silently ignoring a warning is not a pass.

Record the EXE size, modification time, and SHA-256 hash with:

```powershell
Get-FileHash .\dist\AccessibleAIWorkflowConfigurate.exe -Algorithm SHA256
```

Inspect the ZIP before sharing it:

```powershell
Get-ChildItem .\dist\AccessibleAIWorkflowConfigurate-local.zip
tar -tf .\dist\AccessibleAIWorkflowConfigurate-local.zip
```

Confirm it contains the EXE and the user docs, and contains no source checkout, secrets, caches, or unrelated files. Record the ZIP SHA-256 too.

## Documentation gate

- README has name, purpose, system requirements, install, uninstall, privacy, support, and known limitations.
- Release notes state what changed and the exact checks that passed.
- Accessibility checklist states what was manually tested and what still needs NVDA.
- Version and artifact hashes are recorded, or the candidate is explicitly marked `Unreleased`.
- License and distribution status are stated. Do not invent a license; choose one before public distribution.

## Manual NVDA gate

With NVDA running, open the packaged EXE and verify:

1. The title is `Accessible AI Workflow Configurate`.
2. `Start guided change` announces the current category and question.
3. `Guided help` explains what to do at each step.
4. `All sources` lists source names and counts and opens the selected source.
5. `What this changes` is announced before the value editor.
6. Closing a dialog returns focus to the control that opened it.
7. No value is saved during this check.
8. Tab and Shift+Tab reach every visible control once, in a sensible order.
9. Errors are announced, actionable, and recoverable with the keyboard.
10. Back, Next, Skip, Cancel, and Close work without trapping focus.
11. Restarting the app preserves saved changes and does not create a new warning.

Automated tests and accessibility trees do not replace this spoken-output check.

## Sign-off record

Record these before sharing:

- commit: `git rev-parse HEAD`
- EXE hash and ZIP hash
- test result count
- Windows version
- NVDA version and result
- known limitations
- exact folder or channel where the local artifact was shared

If any item is unknown, the candidate is not release-ready.

## Release boundary

This checklist creates local evidence only. Push, pull request, merge, tagging, publication, installer signing, and deployment require a separate explicit decision.
