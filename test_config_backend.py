import json, tempfile, os, subprocess
from pathlib import Path
import config_backend as b


def test_home_and_categories_are_current_user_safe(monkeypatch, tmp_path):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert b._user_home() == tmp_path
    settings = [
        b.Setting(("permissions", "network"), "permissions.network", "true", "boolean"),
        b.Setting(("custom",), "custom", "x", "string"),
    ]
    groups = b.group_settings(settings)
    assert groups["Permissions"][0] == settings[0]
    assert groups["custom"][0] == settings[1]
    assert len(b.CATEGORY_NAMES) == 19

def test_jsonc_roundtrip_and_hash_guard(monkeypatch, tmp_path):
    p=tmp_path/'x.jsonc'; p.write_text('// keep\n{ "a": 1, "arr": [1, 2] }\n', encoding='utf8')
    f=b.ConfigFile('x',p,'jsonc'); settings,h=b.load_settings(f)
    a=next(x for x in settings if x.path==('a',))
    r=b.save_setting(f,a,'2',h)
    assert json.loads(p.read_text().split('// keep\n',1)[1])['a']==2
    assert r.backup_path.exists()
    try: b.save_setting(f,a,'3',h); assert False
    except RuntimeError: pass

def test_toml_preserves_comments(tmp_path, monkeypatch):
    if b.tomlkit is None: return
    p=tmp_path/'x.toml'; p.write_text('# keep\na = 1\n',encoding='utf8')
    f=b.ConfigFile('x',p,'toml'); s,h=b.load_settings(f); b.save_setting(f,s[0],'2',h)
    assert '# keep' in p.read_text() and 'a = 2' in p.read_text()

def test_plain_json_uses_jsonc_editor(tmp_path):
    p=tmp_path/'x.json'; p.write_text('{"enabled": false}\n', encoding='utf8')
    f=b.ConfigFile('x',p,'json'); settings,h=b.load_settings(f)
    b.save_setting(f,settings[0],'true',h)
    assert json.loads(p.read_text())['enabled'] is True

def test_markdown_settings_edit_section_body(tmp_path):
    p = tmp_path / 'AGENTS.md'
    p.write_text('# Rules\n\nUse the keyboard.\n\n## Other\nKeep backups.\n', encoding='utf8')
    f = b.ConfigFile('AGENTS.md', p, 'markdown', 'agents')
    settings, digest = b.load_settings(f)
    rules = next(setting for setting in settings if setting.label == 'Rules')
    assert rules.value == 'Use the keyboard.'
    b.save_setting(f, rules, 'Use the keyboard and a screen reader.', digest)
    text = p.read_text(encoding='utf8')
    assert '# Rules' in text
    assert 'Use the keyboard and a screen reader.' in text
    assert '## Other' in text

def test_restore_backup_checks_hash_and_keeps_current_backup(tmp_path):
    p = tmp_path / 'x.json'; p.write_text('{"enabled": false}\n', encoding='utf8')
    f = b.ConfigFile('x', p, 'json')
    settings, digest = b.load_settings(f)
    first = b.save_setting(f, settings[0], 'true', digest)
    saved_digest = b._sha(p.read_bytes())
    second = b.restore_backup(f, first.backup_path, saved_digest)
    assert json.loads(p.read_text())['enabled'] is False
    assert second.backup_path.exists()
    assert len(list(tmp_path.glob('x.json.*.bak'))) == 2

def test_restore_backup_rejects_wrong_file_and_stale_hash(tmp_path):
    p = tmp_path / 'x.json'; p.write_text('{"enabled": false}\n', encoding='utf8')
    other = tmp_path / 'other.json'; other.write_text('{}\n', encoding='utf8')
    f = b.ConfigFile('x', p, 'json')
    settings, digest = b.load_settings(f)
    result = b.save_setting(f, settings[0], 'true', digest)
    try:
        b.restore_backup(f, other, b._sha(p.read_bytes()))
        assert False
    except ValueError:
        pass
    try:
        b.restore_backup(f, result.backup_path, digest)
        assert False
    except RuntimeError:
        pass

def test_restore_oldest_retained_backup_after_pruning(tmp_path):
    p = tmp_path / 'x.json'; p.write_text('{"value": 0}\n', encoding='utf8')
    f = b.ConfigFile('x', p, 'json')
    setting, digest = b.load_settings(f)
    for value in range(1, 7):
        result = b.save_setting(f, setting[0], str(value), digest)
        digest = b._sha(p.read_bytes())
    backups = b.list_backups(f)
    assert len(backups) == 5
    selected = backups[-1]
    selected_bytes = selected.read_bytes()
    restored = b.restore_backup(f, selected, digest)
    assert p.read_bytes() == selected_bytes
    assert restored.backup_path.exists()

def test_boolean_values_are_rejected_when_invalid(tmp_path):
    p = tmp_path / 'x.toml'; p.write_text('enabled = true\n', encoding='utf8')
    f = b.ConfigFile('x', p, 'toml')
    setting, digest = b.load_settings(f)
    try:
        b.save_setting(f, setting[0], 'maybe', digest)
        assert False
    except ValueError:
        pass

def test_malformed_jsonc_is_rejected(tmp_path):
    p = tmp_path / 'broken.jsonc'; p.write_text('{ "enabled": true,\n', encoding='utf8')
    try:
        b.load_settings(b.ConfigFile('broken', p, 'jsonc'))
        assert False
    except subprocess.CalledProcessError:
        pass

def test_discovery_uses_current_user_profile(monkeypatch, tmp_path):
    config = tmp_path / '.codex'; config.mkdir()
    (config / 'config.toml').write_text('enabled = true\n', encoding='utf8')
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    assert any(item.path == config / 'config.toml' for item in b.discover_files())

def test_save_reports_sync_failure_after_file_save(tmp_path, monkeypatch):
    p = tmp_path / 'AGENTS.md'; p.write_text('# Rules\nKeep backups.\n', encoding='utf8')
    f = b.ConfigFile('AGENTS.md', p, 'markdown', 'agents')
    settings, digest = b.load_settings(f)
    monkeypatch.setattr(b, '_sync', lambda _kind: 'sync failed: test')
    result = b.save_setting(f, settings[0], 'Use the keyboard.', digest)
    assert 'sync failed' in result.sync_message
    assert 'Use the keyboard.' in p.read_text(encoding='utf8')

def test_list_backups_returns_only_matching_files_newest_first(tmp_path):
    target = tmp_path / 'x.json'
    target.write_text('{}\n', encoding='utf8')
    older = tmp_path / 'x.json.20260101T010101000000Z.bak'
    newer = tmp_path / 'x.json.20260102T010101000000Z.bak'
    unrelated = tmp_path / 'other.json.20260103T010101000000Z.bak'
    for path in (older, newer, unrelated):
        path.write_text('{}\n', encoding='utf8')
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))
    assert b.list_backups(b.ConfigFile('x', target, 'json')) == [newer, older]
