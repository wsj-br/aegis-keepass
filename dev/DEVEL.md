# Developer guide

This document covers setting up a development environment, cloning the repository, building, testing, and publishing a release of Aegis-KeePass OTP Sync.

## Prerequisites


| Tool                            | Purpose                                 | Notes                            |
| ------------------------------- | --------------------------------------- | -------------------------------- |
| **Git**                         | Clone and version control               |                                  |
| **Python 3.12+**                | Local runs                              | `python3 --version`              |
| **Docker** + **Docker Compose** | Container builds and local Compose runs | Image base: `python:3.13-alpine` |
| **GitHub CLI (**`gh`**)**       | Create GitHub Releases                  | Required only for publishing     |


Optional but recommended:

- A virtual environment tool (`venv`, included with Python)
- SSH key or HTTPS credentials for GitHub



### Install tools (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip

# Docker Engine + Compose plugin (see https://docs.docker.com/engine/install/)
# Example for Ubuntu — follow the official docs for your distro:
#   https://docs.docker.com/engine/install/ubuntu/

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
pip install -r requirements.txt -r requirements-dev.txt
```

Runtime dependencies are listed in `requirements.txt` (Flask, cryptography, RapidFuzz, Gunicorn, pykeepass). Test tools (`pytest`) are in `requirements-dev.txt`.

After changing Python dependencies, refresh third-party license text at the repo root:

```bash
./scripts/update-notices.sh
```

That writes `NOTICES` from a temporary venv with `requirements.txt` via `[pip-licenses](https://pypi.org/project/pip-licenses/)` (PyPI packages), plus fixed Alpine base-image and Impeccable (Apache-2.0) attribution sections.

Deactivate the venv when finished:

```bash
deactivate
```



## Build / run

This project is a Python Flask app. There is no separate compile step for application code. “Build” means installing Python packages locally and/or building the Docker image.

### Local (venv + Gunicorn)

```bash
source .venv/bin/activate
gunicorn --bind 127.0.0.1:8580 --bind '[::1]:8580' --workers 1 --timeout 120 wsgi:app
```

Open [http://127.0.0.1:8580](http://127.0.0.1:8580) (or `http://localhost:8580` — both loopbacks are bound).

Use a **single worker** so in-memory session state stays consistent across requests. Wait until the log shows `Booting worker` before loading the page; opening the URL the instant the process starts can race the worker import.

Useful environment variables (optional):


| Variable                     | Default              | Description                                       |
| ---------------------------- | -------------------- | ------------------------------------------------- |
| `SESSION_TIMEOUT_SECONDS`    | `1800`               | Idle session timeout                              |
| `MAX_IN_MEMORY_UPLOAD_BYTES` | `33554432`           | In-RAM upload threshold (32 MB)                   |
| `MAX_UPLOAD_BYTES`           | `52428800`           | Maximum upload size (50 MB)                       |
| `FLASK_SECRET_KEY`           | *(random per start)* | Set explicitly for stable cookies across restarts |


Example:

```bash
export FLASK_SECRET_KEY=dev-secret
gunicorn --bind 127.0.0.1:8580 --bind '[::1]:8580' --workers 1 --timeout 120 wsgi:app
```



### Docker Compose (recommended smoke environment)

```bash
docker compose up --build --wait && docker compose logs -f
```

`--wait` blocks until the health check passes, then `logs -f` streams Gunicorn output (`Listening at` / `Booting worker`). Note: `--wait` always runs detached, so logs do not appear during the wait itself.

Alternatively, attach immediately (logs stream from the first line; open the UI only after `Booting worker`):

```bash
docker compose up --build
```

Docker publishes the host port before Gunicorn is listening, so opening the UI too early can show a connection reset; a refresh after ready works. Compose maps both `127.0.0.1` and `::1` on port 8580.

Open [http://127.0.0.1:8580](http://127.0.0.1:8580). Stop with `Ctrl+C` or:

```bash
docker compose down
```



### Docker image only

```bash
docker build -t aegis-keepass:dev .
docker run --rm -p 127.0.0.1:8580:8580 -p '[::1]:8580:8580' aegis-keepass:dev
```

The published image uses `python:3.13-alpine` (musl). Local development can stay on Python 3.12+; the image Python may be newer.

### Docker Scout / image policy notes

Release builds attach **SLSA provenance** (`mode=max`) and an **SPDX SBOM** via `[.github/workflows/docker-release.yml](../.github/workflows/docker-release.yml)` so Docker Scout’s supply-chain attestation policy can pass.

Alpine lowers the OS CVE and package surface versus Debian slim. Scout’s **copyleft** policy is still expected to flag the image: Alpine ships GPL components (e.g. BusyBox), and the app depends on `pykeepass` **(GPL-3.0)**. That is accepted; do not chase a copyleft-policy PASS by rewriting the KeePass stack.

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
python -m compileall -q aegis_keepass_lib.py app wsgi.py
python -c "from app import create_app; create_app(); print('OK')"
```

### 3. Health endpoint

With the app running (venv or Docker):

```bash
curl -sf http://127.0.0.1:8580/health && echo
```

Expect HTTP 200.

### 4. Manual smoke test (UI)

1. Start the app (`gunicorn` or `docker compose up --build --wait && docker compose logs -f`).
2. Open [http://127.0.0.1:8580](http://127.0.0.1:8580).
3. Upload an **encrypted** Aegis `.json` backup and a KeePass `.kdbx` (use copies of real files; keep originals safe).
4. Enter passwords (and keyfile if required).
5. Confirm matches on the review page; try a manual link if needed.
6. Download `keepass-merged.kdbx` and open it in KeePassXC / KeePass to verify TOTP fields.
7. Confirm **Start new merge** (after download) or **End session** (during review) returns you to upload with the session cleared.



### 5. Container health check

After Compose is up and healthy:

```bash
docker compose ps
```

Confirm the service is healthy (the image defines a `HEALTHCHECK` against `/health`).

## Publish a new release

Version is defined in a single place: `[app/_version.py](../app/_version.py)`.


| Layer                         | Format   | Example  |
| ----------------------------- | -------- | -------- |
| Git tag / GitHub Release      | `vX.Y.Z` | `v0.1.0` |
| Docker image tag              | `X.Y.Z`  | `0.1.0`  |
| `app/_version.py` / UI footer | `X.Y.Z`  | `0.1.0`  |


Publishing a GitHub Release triggers `[.github/workflows/docker-release.yml](../.github/workflows/docker-release.yml)`, which builds multi-arch images (`linux/amd64`, `linux/arm64`) from `python:3.13-alpine`, attaches SLSA provenance and an SPDX SBOM, and pushes them to `ghcr.io/wsj-br/aegis-keepass`.

### Preparing release notes

Before running the release script, use `[dev/release-new-version-prompt.md](release-new-version-prompt.md)` when preparing a new version. Paste that prompt into Cursor (or another agent) to:

- Create `release-notes/RELEASE_NOTES_X.Y.Z.md` from the `[Unreleased]` section in `dev/CHANGELOG.md`
- Move changelog entries into a versioned section with today's date
- Match the format of prior release notes (highlights, Docker pull/run snippet)

Confirm the prerequisites listed in the prompt (version bump, notes file, clean tree) before continuing with the checklist below.

### Release checklist

1. **Bump the version** in `app/_version.py`:
  ```python
   __version__ = "X.Y.Z"
  ```
2. **Write release notes** at `release-notes/RELEASE_NOTES_X.Y.Z.md`. Use `[dev/release-new-version-prompt.md](release-new-version-prompt.md)` for the full workflow (changelog → notes file, format, and checklist).
3. **Commit** on a clean tree (usually on `main`):
  ```bash
   git status
   git add app/_version.py release-notes/RELEASE_NOTES_X.Y.Z.md
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
  - Reads version from `app/_version.py`
  - Creates annotated tag `vX.Y.Z` at `HEAD` (recreates tag/release if they already exist)
  - Creates a GitHub Release with the notes file
  - Attaches start scripts as release assets:
  `aegis-keepass-start.sh`, `aegis-keepass-start.ps1`, `aegis-keepass-start-wslc.ps1`
  - CI then builds and publishes Docker images
   After publish, assets are available at:
   `https://github.com/wsj-br/aegis-keepass/releases/latest/download/<script-name>`
6. **Watch CI**:
  - Actions: [https://github.com/wsj-br/aegis-keepass/actions](https://github.com/wsj-br/aegis-keepass/actions)
  - Confirm the image appears on GHCR



### Pull and verify the published image

```bash
docker pull ghcr.io/wsj-br/aegis-keepass:X.Y.Z
docker run --rm -p 127.0.0.1:8580:8580 ghcr.io/wsj-br/aegis-keepass:X.Y.Z
```

Or use `latest` when the release was tagged as the newest:

```bash
docker pull ghcr.io/wsj-br/aegis-keepass:latest
```



### Release script options

```bash
./scripts/release.sh --help
./scripts/release.sh --dry-run
./scripts/release.sh --verify-clean=false   # skip clean-tree check (use carefully)
```



## Project layout (developer-oriented)


| Path                                            | Purpose                                                           |
| ----------------------------------------------- | ----------------------------------------------------------------- |
| `app/`                                          | Flask application (routes, templates, static assets)              |
| `aegis_keepass_lib.py`                          | Parsing, decryption, matching, KeePass updates                    |
| `wsgi.py`                                       | Gunicorn entry point                                              |
| `requirements.txt`                              | Python dependencies                                               |
| `Dockerfile` / `docker-compose.yml`             | Container image and local Compose stack                           |
| `app/_version.py`                               | Version source of truth                                           |
| `aegis-keepass-start.sh` / `.ps1` / `-wslc.ps1` | One-command container start; attached to GitHub Releases          |
| `scripts/release.sh`                            | GitHub Release + Docker CI trigger (includes start-script assets) |
| `release-notes/`                                | Per-version release notes consumed by `release.sh`                |
| `dev/release-new-version-prompt.md`             | Agent prompt for preparing release notes and changelog            |
| `dev/CHANGELOG.md`                              | Running change log; source for release notes                      |
| `.github/workflows/docker-release.yml`          | Multi-arch image build/push to GHCR                               |




## Security notes for developers

- Prefer localhost binding (`127.0.0.1:8580`) when testing with real backups.
- Do not commit real Aegis backups, `.kdbx` files, passwords, or keyfiles.
- Memory wiping is best-effort; treat local process memory as sensitive during sessions.



## Workflow

```
                    upload
┌─────────────────┐         ┌─────────────────┐
│  Aegis Backup   │         │  KeePass .kdbx  │
│  (encrypted)    │         │                 │
└────────┬────────┘         └────────┬────────┘
         │                           │
         └─────────────┬─────────────┘
                       ▼
           ┌──────────────────────┐
           │  Web App (Docker)    │
           │  match · apply       │
           └──────────┬───────────┘
                      │ download (browser)
                      ▼
           ┌────────────────────────┐
           │  keepass-merged.kdbx   │
           │  (replace in KeePass)  │
           └────────────────────────┘
```

