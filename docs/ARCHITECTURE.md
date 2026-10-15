# Architecture

## Components

- `workflow_config_editor.py`: wxPython persistent list-detail editor, guided checklist/wizard, explanations, validation, presets, summaries, health checks, accessibility labels, focus flow, save, undo.
- `config_backend.py`: discovery, typed parsing, hashing, backups, atomic saves, restore, and synchronization.
- `jsonc_bridge.cjs`: Microsoft `jsonc-parser` bridge for format-preserving JSONC edits.
- `workflow_config_editor.spec`: PyInstaller one-file build definition.

## Data flow

```text
discover files -> load settings + SHA-256
       -> choose category/setting -> edit current/pending value
       -> hash-checked typed save -> backup + atomic replace -> optional sync
       -> optional confirmed undo -> hash-checked restore

Guided state stays in memory until an explicit save. Presets are previewed through the same pending-value and review path. Recent changes are session-only metadata; health checks are read-only.
```

The backend resolves the current Windows user's profile from `USERPROFILE`, falling back to `Path.home()`. It never reads credentials or runtime state as editable settings.

## Verification

Fixture tests cover JSON/JSONC round trips, TOML comment preservation, hash guards, category grouping, current-user resolution, backup retention, and undo. The GUI has a no-write `--smoke` path. Packaging must be followed by both packaged smoke and normal-startup checks.
