# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2026-07-14

### Added
- One-command container start scripts at repo root: `aegis-keepass-start.sh` (Linux/macOS), `aegis-keepass-start.ps1` (Docker Desktop), and `aegis-keepass-start-wslc.ps1` (WSL Containers / `wslc`).
- `scripts/release.sh` attaches the three start scripts as GitHub Release assets (`releases/latest/download/...`).

## [0.1.1] - 2026-07-12

### Added
- Developer guide at `dev/DEVEL.md` (environment setup, build, test, release).
- Agent instructions at `AGENT.md` requiring changelog updates for meaningful changes.
- Step 3 download completion view after saving the merged database: header advances to Download, with a summary of total KeePass entries, entries with OTP, updated count, and cleaned count, plus an End session button; the review toolbar and entry table are hidden on this screen.

### Fixed
- Slow KeePass database opening on large vaults: `entries_from_db` no longer runs repeated pykeepass XPath tree scans per entry (recycle-bin lookup, group path, and string fields are read in a single pass via lxml ancestor traversal).

### Changed
- After download, the review page shows the completion summary instead of auto-redirecting to upload; the user returns to upload only when they click End session.
- Gunicorn worker request timeout increased from 120s to 300s in `Dockerfile` to accommodate large-database unlock and load on slow hosts.
