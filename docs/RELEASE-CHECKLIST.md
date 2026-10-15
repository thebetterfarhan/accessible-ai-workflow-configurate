# Accessible AI Workflow Configurate release checklist

Use this checklist before sharing a build. It verifies the local portable EXE and does not publish anything.

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

Record the EXE size, modification time, and SHA-256 hash with:

```powershell
Get-FileHash .\dist\AccessibleAIWorkflowConfigurate.exe -Algorithm SHA256
```

## Manual NVDA gate

With NVDA running, open the packaged EXE and verify:

1. The title is `Accessible AI Workflow Configurate`.
2. `Start guided change` announces the current category and question.
3. `Guided help` explains what to do at each step.
4. `All sources` lists source names and counts and opens the selected source.
5. `What this changes` is announced before the value editor.
6. Closing a dialog returns focus to the control that opened it.
7. No value is saved during this check.

Automated tests and accessibility trees do not replace this spoken-output check.

## Release boundary

This checklist creates local evidence only. Push, pull request, merge, tagging, publication, installer signing, and deployment require a separate explicit decision.
