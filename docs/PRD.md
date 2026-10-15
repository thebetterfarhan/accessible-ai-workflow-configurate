# Accessible AI Workflow Configurate PRD

## Status

Safe interaction slices are implemented in the local EXE: guided mode, review-before-save, backup history, keyboard shortcuts, focus recovery, and empty-state guards. Release readiness still needs a live NVDA walkthrough and a signed distribution decision.

## Problem

Codex, OpenCode, and CommandCode keep workflow behavior in different TOML, JSON, JSONC, and instruction files. Raw editors expose implementation details, make related settings hard to find, and are difficult to operate with a screen reader.

## Users

- Windows users who configure AI coding workflows.
- NVDA users who need a predictable keyboard-first interface.
- Maintainers who need backups and recovery before changing workflow behavior.

## Goals

1. Let a user change one workflow setting through a persistent list-detail editor.
2. Use clear questions and native controls: radio choices, checkboxes, and text fields.
3. Group settings into understandable categories and show all 19 categories with counts, including empty categories.
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

The guided entry point opens a keyboard-friendly category-by-category wizard. It adapts to the loaded configuration's categories, explains each category's purpose and the available values, uses Back/Next/Skip navigation, and asks the minimum required questions: category, setting, value, and final check. Each saved category advances to the next one without losing the previous answer.

The welcome orientation and guidance toggle support new users who need either detailed or shorter spoken instructions.

Guided setup exposes a category checklist and can pause and resume within the current session without writing a partial change.

Guided Next validates the current answer before advancing and provides a type-specific example for free-form values.

Each guided step exposes one plain-language action cue so a new user knows what to do before pressing Next.

The change summary shows old and new values, while category reset discards only the current pending answer after confirmation.

Safe presets are preview-only until the existing review/save action is confirmed. Recent changes and health checks are read-only views.

The `All sources` read-only view lists every supported source found for the current user and totals their editable settings. The configuration selector remains the editing entry point for one source at a time, and the inventory explains that authentication, runtime, history, and cache files are excluded.

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

Markdown instruction files expose editable section bodies and identify them in the editor as `markdown section body`; generated TASTE sections remain protected.

Credentials, auth files, runtime history, state, and caches are excluded. Backup files may be listed read-only for recovery and are never edited as settings.

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
- Guided mode provides orientation, category progress, pause/resume, validation before Next, explanations, summaries, presets, recent changes, and health checks.
- Presets never write without an explicit review and save confirmation.
- Health and recent-change views are read-only.
- All sources lists the discovered supported sources and the total editable setting count without exposing raw values.
- Guided steps show a plain-language action cue and make clear that answers are not saved until the review and save actions.
- A fixture save preserves comments and rejects an external hash change.
- A fixture undo restores the exact prior bytes and keeps a recovery backup.
- Review-before-save shows the target, current value, and pending value before writing.
- Backup history lists valid backups newest first and restores only after confirmation.
- Restoring the oldest retained backup works when the five-backup limit is full.
- Malformed JSONC and invalid boolean values are rejected before writing.
- A synchronization failure is reported as a warning after the edited file has been safely saved.
- Guided mode announces the four configuration questions and uses the same safe save path.
- A live NVDA walkthrough completes configuration, category, setting, edit, and save actions without focus loss.

## Open decisions

- Choose a signed installer or a portable EXE for distribution.
- Decide whether to publish the bundled Node runtime or require an existing runtime.
- Complete live NVDA validation on a representative Windows account.
