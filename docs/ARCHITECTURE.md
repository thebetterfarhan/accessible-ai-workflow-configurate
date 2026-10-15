# Architecture

## Components

- `workflow_config_editor.py`: wxPython persistent list-detail editor, guided checklist/wizard, explanations, validation, presets, summaries, read-only source inventory and health checks, accessibility labels, focus flow, save, undo.
- `config_backend.py`: discovery, typed parsing, hashing, backups, atomic saves, restore, and synchronization.
- `jsonc_bridge.cjs`: Microsoft `jsonc-parser` bridge for format-preserving JSONC edits.
- `workflow_config_editor.spec`: PyInstaller one-file build definition.

## Data flow

```text
discover files -> load settings + SHA-256
       -> choose category/setting -> edit current/pending value
       -> hash-checked typed save -> backup + atomic replace -> optional sync
       -> optional confirmed undo -> hash-checked restore
```

Guided state stays in memory until an explicit save. Presets are previewed through the same pending-value and review path. Recent changes are session-only metadata; health checks are read-only.

The source inventory reparses discovered files only to count editable settings. It shows names and counts, never raw values, and keeps credential, runtime, history, and cache files outside the editable source list.

The backend resolves the current Windows user's profile from `USERPROFILE`, falling back to `Path.home()`. It never reads credentials or runtime state as editable settings.

Backup restoration reads the selected backup before retention pruning, so the oldest retained backup remains restorable. JSONC parse errors and invalid typed values fail before a write; instruction synchronization is reported separately after the file write.

## Verification

Fixture tests cover JSON/JSONC round trips, TOML comment preservation, hash guards, category grouping, current-user resolution, backup retention, and undo. The GUI has a no-write `--smoke` path. Packaging must be followed by both packaged smoke and normal-startup checks.
