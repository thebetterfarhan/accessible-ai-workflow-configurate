from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
hiddenimports = ["config_backend", *collect_submodules("tomlkit")]
a = Analysis(
    [str(root / "workflow_config_editor.py")],
    pathex=[str(root)],
    binaries=[(str(root / "node.exe"), ".")],
    datas=[
        (str(root / "jsonc_bridge.cjs"), "."),
        (str(root / "node_modules" / "jsonc-parser"), "node_modules/jsonc-parser"),
    ],
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="WorkflowConfigEditor", console=False)
