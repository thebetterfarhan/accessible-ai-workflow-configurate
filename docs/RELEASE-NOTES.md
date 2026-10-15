# Accessible AI Workflow Configurate v0.0.1 local release candidate

## Included

- Accessible AI Workflow Configurate portable Windows EXE.
- Guided setup with Back, Next, Skip category, pause, resume, validation, and plain-language help.
- All sources inventory with direct source launching and whole-workflow health checks.
- Plain-language `What this changes` guidance for selected settings.
- Review-before-save, hash checks, timestamped backups, backup history, and undo.
- TOML, JSON, JSONC, and Markdown section editing with UTF-8 BOM support for JSONC.
- MIT source license and third-party notices for the bundled Node.js runtime and `jsonc-parser` parser.

## Verification

- 14 Python tests passed.
- Python and Node syntax checks passed.
- npm audit reported zero high-severity vulnerabilities.
- Source and packaged smoke checks passed.
- NVDA walkthrough passed for the renamed app, guided help, source inventory, and setting explanations.
- Local ZIP includes `THIRD-PARTY-NOTICES.md` and both bundled license texts.

Artifact hashes are recorded in [`RELEASE-SIGNOFF.md`](RELEASE-SIGNOFF.md), which stays with the repository evidence and is not embedded in the ZIP.

## Boundary

This is a local release candidate. It has not been pushed, tagged, published, signed, or deployed.
