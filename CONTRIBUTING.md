# Contributing

## Local setup

```powershell
python -m pip install --user -r requirements.txt
npm install --ignore-scripts
```

The editor needs wxPython, `tomlkit`, Node.js, and `jsonc-parser`. Do not commit `node.exe`, `node_modules`, `build`, or `dist`; they are local build inputs or outputs.

## Checks

```powershell
python -m pytest -q
python -m py_compile workflow_config_editor.py config_backend.py
node --check jsonc_bridge.cjs
python workflow_config_editor.py --smoke
```

For a package check:

```powershell
python -m PyInstaller --noconfirm --clean workflow_config_editor.spec
dist\WorkflowConfigEditor.exe --smoke
```

Do not test by saving a real user configuration. Use fixture files. Never commit secrets, auth files, personal configuration values, generated binaries, or backup files.

