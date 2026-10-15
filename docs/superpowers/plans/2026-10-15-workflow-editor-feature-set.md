# Workflow Config Editor Feature Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Workflow Config Editor friendly for new users by adding guided orientation, resumable category work, validation, summaries, safe presets, recovery history, health checks, and adjustable screen-reader guidance.

**Architecture:** Keep the existing injected backend and persistent list-detail editor. Add small stateful helpers to `workflow_config_editor.py` for wizard state, summaries, presets, health checks, and accessibility copy; keep all writes behind the existing hash-checking save and backup paths. Extend smoke assertions rather than adding a new UI dependency.

**Tech Stack:** Python 3.12, wxPython, pytest, PyInstaller, existing TOML/JSONC/Markdown backend.

**Spec:** `docs/PRD.md`

## Global Constraints

- Preserve keyboard-only operation and named controls for NVDA.
- Keep atomic writes, hash checks, timestamped backups, undo, and generated TASTE protection.
- Do not edit credentials, auth, caches, runtime history, or third-party provider defaults.
- Use TDD: every behavior change has a failing smoke or backend test before implementation.
- Commit each completed slice locally; do not push, create a PR, publish, or deploy.
- Rebuild `dist\\WorkflowConfigEditor.exe` and run packaged `--smoke` after UI changes.
- Leave live NVDA speech/focus validation as an explicit manual gate.

## Review Focus

- Wizard resume must not lose pending answers or silently overwrite files.
- `Next` must block invalid values and focus the failing control with a spoken explanation.
- Presets and category reset must show exact changes before writing anything.
- Health checks must report malformed or ignored settings without repairing automatically.
- Verbosity changes must alter spoken guidance without removing labels or keyboard access.

### Task 1: First-run orientation and verbosity

**Files:**
- Modify: `workflow_config_editor.py`
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/ACCESSIBILITY-CHECKLIST.md`

**Interfaces:**
- Add `_show_first_run_help()` and `_set_guidance_level(level: str)` to `ConfigEditorFrame`.
- Add a persisted-in-session `guidance_level` with `short` and `detailed` values; default `detailed`.

- [ ] Add a failing smoke assertion for a welcome message, a `Guidance detail` control, and short/detailed text differences.
- [ ] Run `python workflow_config_editor.py --smoke` and confirm the new assertion fails.
- [ ] Implement the welcome dialog and verbosity control using native wx controls and keyboard focus restoration.
- [ ] Run source smoke, pytest, compile, and diff checks.
- [ ] Update docs and commit `feat: add first-run accessibility orientation`.
- [ ] Rebuild and run packaged smoke.

### Task 2: Category checklist and resumable wizard state

**Files:**
- Modify: `workflow_config_editor.py`
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/ACCESSIBILITY-CHECKLIST.md`

**Interfaces:**
- Add `_guided_completed: set[str]`, `_guided_resume_state()`, and `_resume_guided()`.
- Expose a spoken checklist label for each category: `Not started`, `In progress`, or `Done`.

- [ ] Add failing smoke assertions for checklist states and resume after cancel/close.
- [ ] Run smoke to confirm failure.
- [ ] Implement checklist state without writing user files; save only after the existing review confirmation.
- [ ] Verify back/next/skip and resume preserve answers.
- [ ] Update docs and commit `feat: add resumable guided checklist`.
- [ ] Rebuild and run packaged smoke.

### Task 3: Validation, examples, and option explanations

**Files:**
- Modify: `workflow_config_editor.py`
- Modify: `test_config_backend.py` only if a backend fixture is needed.
- Modify: docs listed above.

**Interfaces:**
- Add `_guided_validation_error()` and `_value_example(setting)`.
- `Next` must call the same validation used by Review and focus the invalid control.

- [ ] Add failing smoke assertions for blocked Next, focus restoration, and example text.
- [ ] Run smoke to confirm failure.
- [ ] Implement validation-before-Next and concise examples for text, JSON, number, boolean, and Markdown values.
- [ ] Run pytest, smoke, compile, and diff checks; commit `feat: validate guided answers before next`.
- [ ] Rebuild and run packaged smoke.

### Task 4: Change summary and category reset

**Files:**
- Modify: `workflow_config_editor.py`
- Modify: docs listed above.

**Interfaces:**
- Add `_guided_changes: list[dict[str, str]]`, `_change_summary_text()`, and `_reset_category()`.

- [ ] Add failing smoke assertions for summary rows and reset confirmation.
- [ ] Run smoke to confirm failure.
- [ ] Implement summary review for all staged category changes and a guarded reset that restores loaded values without touching disk until Save.
- [ ] Run checks; commit `feat: add guided change summary and reset`.
- [ ] Rebuild and run packaged smoke.

### Task 5: Safe presets

**Files:**
- Modify: `workflow_config_editor.py`
- Modify: `README.md`, `docs/PRD.md`, `docs/ACCESSIBILITY-CHECKLIST.md`

**Interfaces:**
- Add `_preset_choices()` and `_preset_changes(name: str) -> list[tuple[Any, str]]`.
- Presets must be opt-in, empty when no safe metadata exists, and always pass through the summary/review flow.

- [ ] Add failing smoke assertions for preset preview and no implicit save.
- [ ] Run smoke to confirm failure.
- [ ] Implement beginner/balanced/advanced only for known local setting types; never embed provider URLs, credentials, or identities.
- [ ] Run checks; commit `feat: add previewable workflow presets`.
- [ ] Rebuild and run packaged smoke.

### Task 6: Recent changes and category recovery

**Files:**
- Modify: `workflow_config_editor.py`
- Modify: docs listed above.

**Interfaces:**
- Add in-session `_recent_changes` entries with setting, old value, new value, timestamp, and backup path.
- Reuse `list_backups` and `restore_backup`; never bypass external-change checks.

- [ ] Add failing smoke assertions for recent-change announcements and recovery entry selection.
- [ ] Run smoke to confirm failure.
- [ ] Implement a read-only recent changes dialog and guarded restore/reset action.
- [ ] Run checks; commit `feat: add recent workflow changes`.
- [ ] Rebuild and run packaged smoke.

### Task 7: Configuration health check

**Files:**
- Modify: `workflow_config_editor.py`
- Modify: `config_backend.py` only if a read-only validation helper is required.
- Modify: docs listed above.

**Interfaces:**
- Add `_health_report()` returning `(severity, message)` rows for parse errors, ignored settings, unavailable files, and protected sections.

- [ ] Add failing smoke/backend assertions for healthy, malformed, and ignored-setting reports.
- [ ] Run the focused test to confirm failure.
- [ ] Implement a read-only Health check dialog with actionable wording and no automatic repair.
- [ ] Run checks; commit `feat: add configuration health check`.
- [ ] Rebuild and run packaged smoke.

### Task 8: Full verification and documentation gate

**Files:**
- Modify: `README.md`, `docs/PRD.md`, `docs/ACCESSIBILITY-CHECKLIST.md`, `docs/ARCHITECTURE.md`.

- [ ] Run `python -m pytest -q`.
- [ ] Run source `--smoke` and `python -m py_compile workflow_config_editor.py config_backend.py`.
- [ ] Run `git diff --check` and inspect staged files for secrets, credentials, logs, and generated artifacts.
- [ ] Rebuild the EXE and run packaged `--smoke`.
- [ ] Perform live NVDA walkthrough for welcome, checklist, resume, validation, summary, presets, recovery, health check, and verbosity.
- [ ] Commit documentation updates only after the walkthrough result is recorded.

