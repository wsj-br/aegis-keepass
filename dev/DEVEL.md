# Developer guide

This document covers setting up a development environment, cloning the repository, building, testing, and publishing a release of Aegis-KeePass OTP Sync.

## Prerequisites

| Tool | Purpose | Notes |
|------|---------|-------|
| **Git** | Clone and version control | |
| **Python 3.12+** | Local runs and tests | `python3 --version` |
| **GitHub CLI (`gh`)** | Create GitHub Releases | Required only for publishing |

Optional but recommended:

- A virtual environment tool (`venv`, included with Python)
- SSH key or HTTPS credentials for GitHub

Desktop development also needs the system WebView libraries described in [packaging/README.md](../packaging/README.md) (GTK/WebKit on Linux, WebView2 on Windows, nothing extra on macOS).

### Install tools (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip \
  gir1.2-gtk-3.0 gir1.2-webkit2-4.1 libwebkit2gtk-4.1-dev \
  pkg-config python3-gi

# GitHub CLI (see https://cli.github.com/)
# Example:
#   sudo apt install -y gh
```

Authenticate the GitHub CLI before releasing:

```bash
gh auth login
```

## Clone the repository

```bash
git clone git@github.com:wsj-br/aegis-keepass.git
cd aegis-keepass
```

HTTPS alternative:

```bash
git clone https://github.com/wsj-br/aegis-keepass.git
cd aegis-keepass
```

## Install the development environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt -r requirements-desktop.txt
```

Runtime dependencies are listed in `requirements.txt` (Flask, cryptography, RapidFuzz, pykeepass). Test tools (`pytest`) are in `requirements-dev.txt`. The desktop shell (`pywebview`, `waitress`, `pyinstaller`) is in `requirements-desktop.txt`.

### Upgrade packages in an existing venv

Requirements use minimum versions (`>=`), so a plain `pip install -r …` leaves already-installed packages alone if they already satisfy those floors. To upgrade pip and the latest releases allowed by every `requirements*.txt` file:

```bash
./scripts/upgrade-dependencies.sh
```

That uses `.venv` when it exists, upgrades pip, setuptools, and wheel, then upgrades `requirements.txt`, `requirements-dev.txt`, and `requirements-desktop.txt`. It regenerates `NOTICES` from `requirements.txt` afterward. Pass `--skip-notices` to leave `NOTICES` unchanged, or `--python=PATH` to target another interpreter. The script does not replace the Python installation itself.

## Version

`app/_version.py` is the only copy of the release version. The window footer, the macOS bundle version, and CI read it from there.

```bash
./scripts/version
./scripts/version 0.2.0
```

The argument must be `MAJOR.MINOR.PATCH` (digits only). The script does not edit the changelog or past release notes.

## Build / run

There is no separate compile step for application code. Day-to-day work uses `scripts/dev`. Release binaries are built with PyInstaller.

### Desktop window

```bash
./scripts/dev
```

`desktop_main.py` sets `AK_DESKTOP=1`, starts Waitress on loopback, and opens a native window at **750×660** (`min_size` 700×600). Save uses a native Save dialog via `window.pywebview.api.download_merged`.

Useful environment variables (optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_TIMEOUT_SECONDS` | `1800` | Idle session timeout |
| `MAX_IN_MEMORY_UPLOAD_BYTES` | `33554432` | In-RAM upload threshold (32 MB) |
| `MAX_UPLOAD_BYTES` | `52428800` | Maximum upload size (50 MB) |
| `FLASK_SECRET_KEY` | *(random per start)* | Set explicitly for stable cookies across restarts |

### Loopback HTTP (no window)

Use this when you want a browser or `curl` against the same app:

```bash
export FLASK_SECRET_KEY=dev-secret   # optional
./scripts/dev --http
```

Open [http://127.0.0.1:8580](http://127.0.0.1:8580). The process is a single Waitress server. It also binds `::1` when the host allows it. Pass `--port 9090` to use another port.

This mode does not set `AK_DESKTOP`, so the pages say Upload / Download and the browser saves the merged file. The packaged app and `./scripts/dev` (no flag) say Read / Save and use the native dialog.

### Package a binary

```bash
./scripts/build-desktop.sh
```

On Linux this writes `dist/aegis-keepass` and an AppImage beside it. A current Ubuntu, Debian, or Zorin OS desktop already has GTK 3 and WebKitGTK 4.1. On Windows the script writes `dist/aegis-keepass.exe` and an Inno Setup installer beside it. On macOS it also writes a drag-to-Applications DMG under `dist/`. See [packaging/README.md](../packaging/README.md).

**CI / release artifacts:** publishing a GitHub Release (via `scripts/release.sh`) triggers [`.github/workflows/desktop-release.yml`](../.github/workflows/desktop-release.yml), which builds on native runners and uploads:

| Artifact | Runner |
|----------|--------|
| `aegis-keepass-<ver>-linux-amd64.AppImage` | `ubuntu-latest` |
| `aegis-keepass-<ver>-linux-arm64.AppImage` | `ubuntu-24.04-arm` |
| `aegis-keepass-<ver>-macos-intel.dmg` | `macos-15-intel` |
| `aegis-keepass-<ver>-macos-arm64.dmg` | `macos-15` |
| `aegis-keepass-<ver>-windows-x64.exe` | `windows-latest` |
| `aegis-keepass-<ver>-windows-arm64.exe` | `windows-11-arm` |

macOS artifacts include a `.dmg.sha256` file. `scripts/release.sh` does not upload binaries; the workflow does, after the release is published.

## Test

### 1. Automated suite (pytest)

With the venv activated and `requirements-dev.txt` installed:

```bash
pytest
```

This runs library unit tests and Flask API/integration tests under `tests/`. Synthetic encrypted Aegis and KeePass fixtures are generated at runtime (no vault files are committed). Prefer `pytest` after non-trivial changes to matching, upload/review routes, or session/secure code.

Useful variants:

```bash
pytest -q
pytest tests/unit
pytest tests/integration
```

### 2. Syntax / import check

With the venv activated:

```bash
python -m compileall -q aegis_keepass_lib.py app desktop_main.py
python -c "from app import create_app; create_app(); print('OK')"
```

### 3. App is serving

With `./scripts/dev --http` running:

```bash
curl -sf -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8580/
```

Expect HTTP 200.

### 4. Manual smoke test (UI)

1. Start the app (`./scripts/dev` or `./scripts/dev --http`).
2. Open the window, or [http://127.0.0.1:8580](http://127.0.0.1:8580) for `--http`.
3. Read an **encrypted** Aegis `.json` backup and a KeePass `.kdbx` (use copies of real files; keep originals safe).
4. Enter passwords (and keyfile if required).
5. Confirm matches on the review page; try a manual link if needed.
6. Save `keepass-merged.kdbx` and open it in KeePassXC / KeePass to verify TOTP fields.
7. Confirm **Start new merge** (after save) or **End session** (during review) returns you to the first screen with the session cleared.

## Publish a new release

Version is defined in a single place: [`app/_version.py`](../app/_version.py).

| Layer | Format | Example |
|-------|--------|---------|
| Git tag / GitHub Release | `vX.Y.Z` | `v0.2.1` |
| `app/_version.py` / UI footer | `X.Y.Z` | `0.2.1` |
| Release asset filenames | `aegis-keepass-X.Y.Z-<platform>` | `aegis-keepass-0.2.1-linux-amd64.AppImage` |

Publishing a GitHub Release triggers [`.github/workflows/desktop-release.yml`](../.github/workflows/desktop-release.yml), which builds the six desktop artifacts and attaches them to that release.

### Preparing release notes

Before running the release script, use [`dev/release-new-version-prompt.md`](release-new-version-prompt.md) when preparing a new version. Paste that prompt into Cursor (or another agent) to:

- Create `release-notes/RELEASE_NOTES_X.Y.Z.md` from the `[Unreleased]` section in `dev/CHANGELOG.md`
- Move changelog entries into a versioned section with today's date
- Match the format in the prompt: highlights (ending with a line linking to `dev/CHANGELOG.md` for the detailed changes), then an Install section last that names the six desktop assets

Confirm the prerequisites listed in the prompt (version bump, notes file, clean tree) before continuing with the checklist below.

### Release checklist

1. **Bump the version**:
   ```bash
   ./scripts/version X.Y.Z
   ```
2. **Write release notes** at `release-notes/RELEASE_NOTES_X.Y.Z.md`. Use [`dev/release-new-version-prompt.md`](release-new-version-prompt.md) for the full workflow (changelog → notes file, format, and checklist).
3. **Commit** on a clean tree (usually on `main`):
   ```bash
   git status
   git add app/_version.py release-notes/RELEASE_NOTES_X.Y.Z.md dev/CHANGELOG.md
   git commit -m "Release X.Y.Z"
   git push origin HEAD
   ```
4. **Validate** the release script (no side effects):
   ```bash
   ./scripts/release.sh --dry-run
   ```
5. **Publish**:
   ```bash
   ./scripts/release.sh
   ```
   Requirements for the script:
   - `gh` authenticated (`gh auth login`)
   - Clean working tree (or pass `--verify-clean=false`)
   - `app/_version.py` and matching `release-notes/RELEASE_NOTES_<version>.md`
   - Remote `origin` configured

   What the script does:
   - Reads the version with `scripts/version`
   - Creates annotated tag `vX.Y.Z` at `HEAD` (recreates tag/release if they already exist)
   - Creates a GitHub Release with the notes file
   - CI then builds and attaches the desktop artifacts (`desktop-release.yml`)

6. **Watch CI**:
   - Actions: https://github.com/wsj-br/aegis-keepass/actions
   - Confirm the six desktop files (two AppImages, two installers, two DMGs, and the two macOS `.dmg.sha256` files) appear on the GitHub Release

### Release script options

```bash
./scripts/release.sh --help
./scripts/release.sh --dry-run
./scripts/release.sh --verify-clean=false   # skip clean-tree check (use carefully)
```

## Project layout (developer-oriented)

| Path | Purpose |
|------|---------|
| `app/` | Flask application (routes, templates, static assets) |
| `aegis_keepass_lib.py` | Parsing, decryption, matching, KeePass updates |
| `desktop_main.py` | Desktop entrypoint (Waitress + pywebview) |
| `requirements.txt` | Python dependencies |
| `requirements-desktop.txt` | Desktop shell deps (pywebview, waitress, pyinstaller) |
| `requirements-dev.txt` | Test deps (pytest) |
| `packaging/aegis-keepass.spec` | PyInstaller spec |
| `packaging/dmg-background.tiff` | Arrow background for the macOS DMG |
| `app/_version.py` | Version source of truth |
| `scripts/version` | Print or set `app/_version.py` |
| `scripts/dev` | Local desktop window, or `--http` loopback server |
| `scripts/build-desktop.sh` | PyInstaller build; DMG on macOS |
| `scripts/package-linux-appimage.sh` | Wrap the Linux build in an AppImage |
| `scripts/package-windows-installer.ps1` | Build the Windows Inno Setup installer |
| `scripts/release.sh` | GitHub Release that triggers desktop CI |
| `scripts/update-notices.sh` | Regenerate root `NOTICES` |
| `scripts/upgrade-dependencies.sh` | Upgrade pip and every `requirements*.txt` package |
| `release-notes/` | Per-version release notes consumed by `release.sh` |
| `dev/release-new-version-prompt.md` | Agent prompt for preparing release notes and changelog |
| `dev/CHANGELOG.md` | Running change log; source for release notes |
| `.github/workflows/desktop-release.yml` | Six-arch PyInstaller builds attached to the GitHub Release |

## Security notes for developers

- Prefer the desktop window or `127.0.0.1` when testing with real backups.
- Do not commit real Aegis backups, `.kdbx` files, passwords, or keyfiles.
- Memory wiping is best-effort; treat local process memory as sensitive during sessions.

## Workflow

```
                    read
┌─────────────────┐         ┌─────────────────┐
│  Aegis Backup   │         │  KeePass .kdbx  │
│  (encrypted)    │         │                 │
└────────┬────────┘         └────────┬────────┘
         │                           │
         └─────────────┬─────────────┘
                       ▼
           ┌──────────────────────┐
           │  Desktop app         │
           │  match · apply       │
           └──────────┬───────────┘
                      │ save
                      ▼
           ┌────────────────────────┐
           │  keepass-merged.kdbx   │
           │  (replace in KeePass)  │
           └────────────────────────┘
```
