# Release 0.1.5

UI polish with light/dark themes and logo, safer download flow, dual-stack localhost readiness, and a local pytest suite.

## Highlights

- **Light / dark themes** — Header control cycles System → Light → Dark; default follows the OS (`prefers-color-scheme`), with WCAG AA contrast for CTAs, chips, toasts, and placeholders.
- **Vault-shield AK logo** — Local favicons and header mark for offline/Docker use (no CDN assets).
- **Password show/hide** — In-control eye toggle on Aegis and KeePass password fields.
- **Download progress modal** — Replaces the browser `confirm()` with stepped merge progress (cleanup → apply OTP → build → download); post-download action renamed to **Start new merge**.
- **No Aegis UUID filter** — Review filter lists matched entries whose KeePass target still lacks an `AegisUUID` marker (first-time links).
- **Touch and accessibility** — Larger hit targets on coarse pointers, safe-area insets, keyboard-reachable drop zones, filter `aria-pressed`, and Escape + focus trap in modals.
- **Ready-before-open** — Compose and start scripts bind both `127.0.0.1` and `::1`, and wait for `/health` before opening or advertising the UI (avoids racing a half-ready server on `localhost`).
- **Hardened Docker packaging** — Narrower build context, `LICENSE`/`NOTICES` in the image, Compose drops all capabilities plus `no-new-privileges`.
- **Pytest suite** — Library unit tests and Flask API/integration tests with synthetic Aegis/KeePass fixtures generated at runtime.

## Docker

```bash
docker pull ghcr.io/wsj-br/aegis-keepass:0.1.5
docker run --rm -p 127.0.0.1:8580:8580 ghcr.io/wsj-br/aegis-keepass:0.1.5
```

Open [http://127.0.0.1:8580](http://127.0.0.1:8580).

Start scripts are also attached as downloadable assets on the [GitHub Release](https://github.com/wsj-br/aegis-keepass/releases/tag/v0.1.5).

## Changes

### Added
- Upload password fields include an in-control show/hide toggle (eye icon) for Aegis and KeePass passwords.
- Review filter **No Aegis UUID** lists matched entries whose KeePass target does not yet have an `AegisUUID` marker (first-time links).
- Approved vault-shield **AK** logo (option A) as local static assets (`app/static/img/logo.png` plus favicons), wired into the header, document icons, and README for offline/Docker use.
- Light/dark color themes with a right-justified header control that cycles System → Light → Dark (sun-dial icon + mode label); default follows the OS (`prefers-color-scheme`), and falls back to dark when the OS preference is undefined.
- Integration guard tests that the UI ships only local static assets (no CDN/fonts/remote scripts) for offline/Docker use.
- Local pytest suite (`tests/`) with library unit tests and Flask API/integration tests; synthetic Aegis/KeePass fixtures are generated at runtime via `tests/fixtures/builders.py` (`requirements-dev.txt`, `pytest.ini`).

### Changed
- Documented that `docker compose up --wait` runs detached (no live Gunicorn logs during wait); recommended follow-up is `docker compose logs -f` to see `Listening` / `Booting worker`.
- Tightened Docker packaging: narrower build context (`.dockerignore`), image ships `LICENSE`/`NOTICES` with `PYTHONUNBUFFERED=1`, and Compose drops all capabilities plus `no-new-privileges` (commented optional `FLASK_SECRET_KEY` passthrough).
- Expanded `.gitignore` for pytest/build caches and user vault dumps (`*.json`, `*.kdbx`, etc.).
- Renamed the post-download action from “End session” to **Start new merge**, since the session is already wiped after download.
- Replaced the browser `confirm()` on Download with an in-app modal that shows stepped merge progress (cleanup → apply OTP → build → download), matching the upload processing pattern; End session uses a matching confirm dialog.
- Polished the operate-mode path: shared `toast.js` (no stacked hide timers), visible `aria-invalid` on fields/drop zones, sticky review table header in a capped scrollport, clearer active-filter focus and progress-error marks, and tokenized leftover type/spacing one-offs.
- Replaced the global `prefers-reduced-motion` `0.01ms` nuke with a targeted policy: static upload-progress active state, instant toasts, and preserved short control color transitions; added shared `--motion-*` tokens and a toast fade/slide entrance.
- Synced `DESIGN.md` with the live Local Vault Desk implementation (AA tokens, fill vs foreground, harden/adapt behaviors; color meta, panel components, touch/safe-area breakpoints).
- Adapted the UI for touch and notched devices: `44px` hit targets on coarse pointers, safe-area insets, `viewport-fit=cover`, and fuller-width review toolbar controls below `900px`.
- Hardened review/upload accessibility: keyboard-reachable file drop zones, labeled search fields, filter `aria-pressed`, table caption/`scope`, and modal Escape + focus trap with stacked conflict dialogs.
- Raised light/dark theme contrast to WCAG AA for CTAs, warning chips, toasts, empty-field text, and placeholders; split fill vs foreground Trust Blue tokens and documented them in `DESIGN.md`.
- Refined operate-mode typography and layout: shared type/spacing tokens, dark-theme reading compensation, header grid (brand / steps / theme), grouped review toolbar, and a `65ch` measure on supporting copy.
- Polished the upload and review UI: tokenized surfaces for both themes, SVG icons instead of emoji, clearer focus states, and removal of the download completion eyebrow.
- Documented pytest install/run steps in `dev/DEVEL.md` and `AGENTS.md` (runtime deps stay in `requirements.txt`).
- `/api/save` now wipes the session immediately after building download bytes instead of relying on `call_on_close` (unreliable under Flask’s test client and delayed wipe).

### Fixed
- First browser load after start no longer races a half-ready server: Compose and start scripts publish both `127.0.0.1` and `::1` (so `localhost` does not stall on IPv6), and the start scripts wait for `/health` before opening or advertising the UI.
- Password field text now stays on the shared UI font stack when shown or hidden (browsers were swapping in a monospace face).
- Upload process steps no longer crash in `finally` after a failed decrypt/open that already destroyed the session (`pending_*` buffers may already be wiped).

---

## Provided start scripts to run the tool locally

| OS                                    | Script                         |
|---------------------------------------|--------------------------------|
| Windows (PowerShell) + Docker Desktop | `aegis-keepass-start.ps1`      |
| Windows (PowerShell) + WSL Containers | `aegis-keepass-start-wslc.ps1` |
| Linux (Bash)                          | `aegis-keepass-start.sh`       |

See [README.md](https://github.com/wsj-br/aegis-keepass/blob/main/README.md) for more details.
