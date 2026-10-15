# Changelog

## Unreleased

### Added

- Guided setup wizard with category and question progress, Back, Next, Skip, pause, resume, validation, examples, and plain-language help.
- All-sources inventory with source counts and direct source opening.
- Whole-workflow health checks with unavailable-source reasons.
- Plain-language `What this changes` explanations for selected settings.
- Review-before-save, timestamped backups, backup history, undo, external-change checks, and recovery backups.
- Accessible keyboard and NVDA verification guidance.

### Fixed

- JSONC files with a UTF-8 byte-order mark now load correctly.
- Invalid boolean values are rejected instead of being silently coerced.
- Backup restore reads the selected backup before pruning old backups.
- Sync failures are reported after a save instead of appearing as an unhandled exception.

### Release boundary

This entry describes the current local release candidate. It is not a published, signed, or deployed release.
