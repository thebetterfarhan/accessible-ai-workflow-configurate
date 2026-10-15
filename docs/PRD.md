# Workflow Config Editor PRD

## Status

Working prototype. The local EXE is usable, but release readiness still needs a live NVDA walkthrough and a signed distribution decision.

## Problem

Codex, OpenCode, and CommandCode keep workflow behavior in different TOML, JSON, JSONC, and instruction files. Raw editors expose implementation details, make related settings hard to find, and are difficult to operate with a screen reader.

## Users

- Windows users who configure AI coding workflows.
- NVDA users who need a predictable keyboard-first interface.
- Maintainers who need backups and recovery before changing workflow behavior.

## Goals

1. Let a user change one workflow setting through a persistent list-detail editor.
2. Use clear questions and native controls: radio choices, checkboxes, and text fields.
3. Group settings into understandable categories and hide empty categories.
4. Preserve comments and formatting in TOML and JSONC files.
5. Prevent silent data loss with hash checks, atomic writes, timestamped backups, and undo.
6. Work for the current Windows user without embedding a developer account path.
7. Keep synchronized instruction and taste files consistent after edits.

## User flow

1. Choose a configuration, using friendly profile names.
2. Choose a populated workflow category.
3. Search for and choose a setting.
4. Choose or enter a new value.
5. Review the current and pending values while editing.
6. Explicitly save, undo the last save, or start another change.

The guided entry point presents the same flow as four spoken questions while keeping the persistent editor visible.

## Accessibility requirements

- Keyboard-only operation.
- Predictable focus order and no focus stealing during list refreshes.
- Every interactive control has a spoken label.
- Status text announces the selected configuration and save result.
- Status text explains the next action and save result.
- NVDA flow uses Tab, Shift+Tab, arrow keys, and Enter without pointer use.
- Escape clears a setting search so an empty result can be recovered without text editing commands.
- Current and pending values are both exposed to the screen reader.
- Live NVDA validation remains a release gate.

## Supported sources

- Codex TOML settings and profiles.
- Codex hooks JSON.
- OpenCode JSONC/JSON settings.
- CommandCode JSON settings.
- Canonical AGENTS.md and taste source files, with synchronization hooks.

Credentials, auth files, history, state, caches, and backup files are excluded.

## Safety and recovery

- Every save checks the file hash read when the configuration was loaded.
- Saves are atomic and create timestamped backups.
- The newest five backups are retained.
- Undo requires confirmation, checks the live hash, and creates a recovery backup before restoring.
- Sync failures are surfaced to the user.

## Non-goals

- Editing credentials or authentication state.
- Sending changes to a remote service.
- Replacing each tool's own configuration semantics.
- Silent bulk rewrites or automatic policy changes.

## Acceptance criteria

- `python -m pytest -q` passes.
- Source and packaged smoke checks pass.
- The EXE starts without an unhandled exception.
- A fixture save preserves comments and rejects an external hash change.
- A fixture undo restores the exact prior bytes and keeps a recovery backup.
- A live NVDA walkthrough completes configuration, category, setting, edit, and save actions without focus loss.

## Open decisions

- Choose a signed installer or a portable EXE for distribution.
- Decide whether to publish the bundled Node runtime or require an existing runtime.
- Complete live NVDA validation on a representative Windows account.
