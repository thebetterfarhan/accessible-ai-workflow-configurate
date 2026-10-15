"""Safe, single-setting editor for the three local agent configurations."""
from __future__ import annotations

import hashlib, json, os, re, shutil, subprocess, tempfile, sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomlkit
except ImportError:  # gives a useful error instead of silently changing format
    tomlkit = None

def _user_home() -> Path:
    """Return the current user's home without embedding the developer account."""
    configured = os.environ.get("USERPROFILE")
    return Path(configured) if configured else Path.home()


CATEGORY_NAMES = (
    "Models", "Providers", "Routing", "Permissions", "Sandbox", "Workspace",
    "Hooks", "Profiles", "Agents", "Taste", "Tools", "Plugins", "MCP",
    "Context", "Output", "Notifications", "Performance", "Security", "Other",
)

@dataclass(frozen=True)
class ConfigFile:
    display_name: str; path: Path; kind: str; sync_kind: str = ""

@dataclass(frozen=True)
class Setting:
    path: tuple[str, ...]; label: str; value: str; value_type: str

    @property
    def category(self) -> str:
        if not self.path:
            return "Other"
        key = self.path[0].casefold()
        for category in CATEGORY_NAMES[:-1]:
            if category.casefold() == key:
                return category
        return self.path[0]

@dataclass(frozen=True)
class SaveResult:
    backup_path: Path; sync_message: str = ""

def _sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def _read(p: Path) -> bytes: return p.read_bytes()

def discover_files() -> list[ConfigFile]:
    home = _user_home()
    c = home / ".codex"; o = home / ".config" / "opencode"; cc = home / ".commandcode"
    out = []
    for p in [c / "config.toml", *sorted(c.glob("*.config.toml")), c / "hooks.json"]:
        if p.is_file(): out.append(ConfigFile(p.name, p, "toml" if p.suffix == ".toml" else "jsonc", ""))
    for p in [o / "opencode.jsonc", o / "opencode.json", cc / "settings.json", cc / "config.json"]:
        if p.is_file(): out.append(ConfigFile(p.name, p, "jsonc", ""))
    a = home / ".codex" / "AGENTS.md"
    if a.is_file(): out.append(ConfigFile("Codex AGENTS.md", a, "markdown", "agents"))
    taste = cc / "taste"
    if taste.is_dir():
        for p in sorted(taste.glob("**/taste.md")):
            out.append(ConfigFile(str(p.relative_to(cc)), p, "markdown", "taste"))
    return out


def group_settings(settings: list[Setting]) -> dict[str, list[Setting]]:
    """Group settings for category controls while retaining source order."""
    groups = {name: [] for name in CATEGORY_NAMES}
    for setting in settings:
        groups.setdefault(setting.category, []).append(setting)
    return {name: values for name, values in groups.items() if values}

def _flatten(x: Any, path=()):
    if isinstance(x, dict):
        for k,v in x.items(): yield from _flatten(v, path+(str(k),))
    elif isinstance(x, list):
        yield Setting(path, ".".join(path), json.dumps(x, ensure_ascii=False), "array")
    elif isinstance(x, bool): yield Setting(path, ".".join(path), str(x).lower(), "boolean")
    elif x is None: yield Setting(path, ".".join(path), "null", "null")
    else: yield Setting(path, ".".join(path), str(x), "number" if isinstance(x,(int,float)) else "string")

def _parse_toml(p):
    if tomlkit is None: raise RuntimeError("tomlkit is required; install requirements.txt")
    return tomlkit.parse(p.read_text(encoding="utf-8"))

def _lookup(doc, path):
    for k in path: doc = doc[k]
    return doc

def load_settings(file: ConfigFile):
    raw = _read(file.path)
    if file.kind == "toml": doc = _parse_toml(file.path); settings = list(_flatten(doc.unwrap()))
    elif file.kind in ("json", "jsonc"): settings = _jsonc_load(file.path)
    else: settings = _markdown_load(file.path, file.sync_kind)
    return settings, _sha(raw)

def _jsonc_load(p):
    node = subprocess.run([_node(), str(Path(__file__).with_name("jsonc_bridge.cjs")), "list", str(p)], capture_output=True, text=True, check=True)
    return [Setting(tuple(x["path"]), x["label"], x["value"], x["value_type"]) for x in json.loads(node.stdout)]

def _markdown_load(p, kind):
    text=p.read_text(encoding="utf-8"); out=[]
    headings = list(re.finditer(r"(?m)^#{1,2}\s+(.+?)\s*$", text))
    for index, m in enumerate(headings):
        name=m.group(1).strip()
        if kind=="agents" and name.startswith("TASTE:"): continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[m.end():end].strip()
        out.append(Setting((name,), name, body, "markdown"))
    return out

def _backup(p):
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    b=p.with_name(p.name+"."+stamp+".bak"); shutil.copy2(p,b)
    backups=sorted(p.parent.glob(p.name+".*.bak"), key=lambda x:x.stat().st_mtime, reverse=True)
    for old in backups[5:]: old.unlink()
    return b

def list_backups(file: ConfigFile) -> list[Path]:
    """Return valid backups for one file, newest first."""
    pattern = re.compile(re.escape(file.path.name) + r"\.\d{8}T\d{6}(?:\d{6})?Z\.bak$")
    return sorted(
        (path for path in file.path.parent.glob(file.path.name + ".*.bak") if pattern.fullmatch(path.name)),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

def save_setting(file: ConfigFile, setting: Setting, new_value: str, expected_sha256: str) -> SaveResult:
    raw=_read(file.path)
    if _sha(raw)!=expected_sha256: raise RuntimeError("external change detected; reload before saving")
    if file.kind == "toml":
        doc=_parse_toml(file.path); cur=doc
        for k in setting.path[:-1]: cur=cur[k]
        old=cur[setting.path[-1]]
        if setting.value_type=="boolean":
            normalized = new_value.strip().lower()
            if normalized not in ("true", "1", "yes", "on", "false", "0", "no", "off"):
                raise ValueError("boolean value must be true or false")
            new = normalized in ("true", "1", "yes", "on")
        elif setting.value_type in ("number",): new=float(new_value) if "." in new_value else int(new_value)
        elif setting.value_type=="array": new=tomlkit.array(json.loads(new_value))
        else: new=new_value
        cur[setting.path[-1]]=new; data=tomlkit.dumps(doc).encode()
    elif file.kind in ("json", "jsonc"):
        data=subprocess.run([_node(),str(Path(__file__).with_name("jsonc_bridge.cjs")),"replace",str(file.path),json.dumps(list(setting.path)),new_value,setting.value_type],capture_output=True,check=True).stdout
    else: data=_markdown_save(raw.decode(), setting, new_value, file.sync_kind).encode()
    backup=_backup(file.path)
    fd,tmp=tempfile.mkstemp(dir=file.path.parent, prefix=".workflow-edit-"); os.close(fd)
    try:
        Path(tmp).write_bytes(data); os.replace(tmp,file.path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    msg=_sync(file.sync_kind) if file.sync_kind else ""
    return SaveResult(backup,msg)

def restore_backup(file: ConfigFile, backup_path: Path | str, expected_sha256: str) -> SaveResult:
    """Restore one of this file's backups after checking the live hash."""
    target = file.path.resolve()
    backup = Path(backup_path).resolve()
    pattern = re.escape(target.name) + r"\.\d{8}T\d{6}(?:\d{6})?Z\.bak"
    if backup.parent != target.parent or not re.fullmatch(pattern, backup.name):
        raise ValueError("backup is not a valid backup for this file")
    if not backup.is_file():
        raise FileNotFoundError(backup)
    raw = _read(target)
    if _sha(raw) != expected_sha256:
        raise RuntimeError("external change detected; reload before restoring")
    selected_bytes = backup.read_bytes()
    current_backup = _backup(target)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".workflow-restore-")
    os.close(fd)
    try:
        Path(tmp).write_bytes(selected_bytes)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    msg = _sync(file.sync_kind) if file.sync_kind else ""
    return SaveResult(current_backup, msg)

def _markdown_save(text, setting, value, kind):
    if kind=="agents" and setting.path[0].startswith("TASTE:"): raise ValueError("generated TASTE block is not editable")
    name = re.escape(setting.path[0])
    match = re.search(rf"(?m)^#{{1,2}}[ \t]+{name}[ \t]*(?:\r?$)", text)
    if not match:
        raise ValueError(f"section not found: {setting.path[0]}")
    next_heading = re.search(r"(?m)^#{1,2}\s+", text[match.end():])
    body_start = match.end()
    body_end = body_start + next_heading.start() if next_heading else len(text)
    body = str(value).strip()
    replacement = ("\n\n" + body + "\n\n") if body else "\n\n"
    return text[:body_start] + replacement + text[body_end:]

def _sync(kind):
    if not kind: return ""
    script=_user_home()/"Documents"/"Codex"/"tools"/("sync-agent-instructions.ps1" if kind=="agents" else "sync-taste.ps1")
    if not script.is_file(): return "sync script unavailable"
    r=subprocess.run(["powershell","-NoProfile","-File",str(script)],capture_output=True,text=True)
    if r.returncode: return "sync failed: " + (r.stderr.strip() or "the synchronization script returned an error")
    return "synchronized"

def _node() -> str:
    bundled = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "node.exe"
    return str(bundled) if bundled.is_file() else "node"
