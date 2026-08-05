# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- First browser load after start no longer races a half-ready server: Compose and start scripts publish both `127.0.0.1` and `::1` (so `localhost` does not stall on IPv6), and the start scripts wait for `/health` before opening or advertising the UI.

### Changed
- Documented that `docker compose up --wait` runs detached (no live Gunicorn logs during wait); recommended follow-up is `docker compose logs -f` to see `Listening` / `Booting worker`.

### Added
- Upload password fields include an in-control show/hide toggle (eye icon) for Aegis and KeePass passwords.
- Review filter **No Aegis UUID** lists matched entries whose KeePass target does not yet have an `AegisUUID` marker (first-time links).
- Added Impeccable (Apache-2.0) attribution to `NOTICES`, preserved by `scripts/update-notices.sh` alongside the Alpine base-image section.
- Approved vault-shield **AK** logo (option A) as local static assets (`app/static/img/logo.png` plus favicons), wired into the header, document icons, and README for offline/Docker use.
- Light/dark color themes with a right-justified header control that cycles System → Light → Dark (sun-dial icon + mode label); default follows the OS (`prefers-color-scheme`), and falls back to dark when the OS preference is undefined.
- Integration guard tests that the UI ships only local static assets (no CDN/fonts/remote scripts) for offline/Docker use.
- Local pytest suite (`tests/`) with library unit tests and Flask API/integration tests; synthetic Aegis/KeePass fixtures are generated at runtime via `tests/fixtures/builders.py` (`requirements-dev.txt`, `pytest.ini`).

### Changed
- Tightened Docker packaging: narrower build context (`.dockerignore`), image ships `LICENSE`/`NOTICES` with `PYTHONUNBUFFERED=1`, and Compose drops all capabilities plus `no-new-privileges` (commented optional `FLASK_SECRET_KEY` passthrough).
- Expanded `.gitignore` for pytest/build caches and allowed committing `.impeccable/design.json` while still ignoring other `*.json` vault dumps.
- Renamed the post-download action from “End session” to **Start new merge**, since the session is already wiped after download.
- Replaced the browser `confirm()` on Download with an in-app modal that shows stepped merge progress (cleanup → apply OTP → build → download), matching the upload processing pattern; End session uses a matching confirm dialog.
- Polished the operate-mode path: shared `toast.js` (no stacked hide timers), visible `aria-invalid` on fields/drop zones, sticky review table header in a capped scrollport, clearer active-filter focus and progress-error marks, and tokenized leftover type/spacing one-offs.
- Replaced the global `prefers-reduced-motion` `0.01ms` nuke with a targeted policy: static upload-progress active state, instant toasts, and preserved short control color transitions; added shared `--motion-*` tokens and a toast fade/slide entrance.
- Synced `DESIGN.md` with the live Local Vault Desk implementation (AA tokens, fill vs foreground, harden/adapt behaviors) and regenerated `.impeccable/design.json` (74 color meta entries, 11 panel components, touch/safe-area breakpoints).
- Adapted the UI for touch and notched devices: `44px` hit targets on coarse pointers, safe-area insets, `viewport-fit=cover`, and fuller-width review toolbar controls below `900px`.
- Hardened review/upload accessibility: keyboard-reachable file drop zones, labeled search fields, filter `aria-pressed`, table caption/`scope`, and modal Escape + focus trap with stacked conflict dialogs.
- Raised light/dark theme contrast to WCAG AA for CTAs, warning chips, toasts, empty-field text, and placeholders; split fill vs foreground Trust Blue tokens and documented them in `DESIGN.md`.
- Refined operate-mode typography and layout: shared type/spacing tokens, dark-theme reading compensation, header grid (brand / steps / theme), grouped review toolbar, and a `65ch` measure on supporting copy.
- Polished the upload and review UI: tokenized surfaces for both themes, SVG icons instead of emoji, clearer focus states, and removal of the download completion eyebrow.
- Documented pytest install/run steps in `dev/DEVEL.md` and `AGENTS.md` (runtime deps stay in `requirements.txt`).
- `/api/save` now wipes the session immediately after building download bytes instead of relying on `call_on_close` (unreliable under Flask’s test client and delayed wipe).

### Fixed
- Password field text now stays on the shared UI font stack when shown or hidden (browsers were swapping in a monospace face).
- Upload process steps no longer crash in `finally` after a failed decrypt/open that already destroyed the session (`pending_*` buffers may already be wiped).

## [0.1.4] - 2026-07-14

### Added
- `scripts/update-notices.sh` regenerates the repo-root `NOTICES` file from `requirements.txt` via `pip-licenses`.
- Added a `LICENSE` file to the repo root for the GPL-3.0 license text.

## [0.1.3] - 2026-07-14

### Changed
- Default listen/host port changed from `8080` to `8580` (Dockerfile, Compose, start scripts, and docs).
- Docker image base switched from `python:3.12-slim` (Debian) to `python:3.13-alpine` for a smaller OS surface and fewer reported CVEs.
- Release workflow now emits SLSA provenance (`mode=max`) and an SPDX SBOM on multi-arch GHCR images.

### Added
- `dev/DEVEL.md` notes for Alpine / Python 3.13 image base, Docker Scout attestation expectations, and why the copyleft policy may still flag the image (`pykeepass` GPL-3.0 and Alpine GPL components).

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
