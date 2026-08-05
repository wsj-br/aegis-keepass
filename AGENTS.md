# Agent instructions

This file gives Cursor and other coding agents project-specific guidance. Follow it in every session where you change this repository.

## Changelog (required)

**Keep [`dev/CHANGELOG.md`](dev/CHANGELOG.md) up to date with all meaningful changes you make.**

The changelog is the running record of work done in the repo. Update it as part of the same task—not as a separate follow-up—whenever you add, change, or remove behavior, configuration, documentation, or release artifacts.

### When to update

Add an entry when you:

- Implement or fix application logic (`app/`, `aegis_keepass_lib.py`, `wsgi.py`)
- Change Docker, Compose, CI, or release tooling
- Add or edit user-facing docs (`README.md`, `release-notes/`, templates, UI copy)
- Change dependencies, environment variables, or defaults
- Add or modify developer docs under `dev/`

**Do not** log trivial edits (typos with no meaning change, whitespace-only diffs, or renames with no behavior change) unless the user explicitly asks.

**Do not** log secrets, passwords, keyfiles, or real backup/database contents.

### Format

Use [Keep a Changelog](https://keepachangelog.com/) style, newest first:

```markdown
## [Unreleased]

### Added
- Short, user- or developer-facing description of what was added.

### Changed
- What changed and why, in plain language.

### Fixed
- Bug fix description.

### Removed
- What was removed and any migration note.

### Security
- Security-relevant change (no exploit details or secrets).
```

Rules:

1. **Always maintain an `[Unreleased]` section** at the top for in-progress work.
2. **One bullet per logical change**—not one bullet per file touched.
3. **Write for humans**: what changed and why it matters, not a git diff summary.
4. **Use present tense or past tense consistently** within a section (prefer past tense: “Added …”, “Fixed …”).
5. **Group under the correct heading** (`Added`, `Changed`, `Fixed`, `Removed`, `Security`). Omit empty sections.
6. When a version is released, move `[Unreleased]` entries into a dated/versioned section (e.g. `## [0.2.0] - 2026-07-12`) and start a fresh `[Unreleased]` section. Release version comes from [`app/_version.py`](app/_version.py). Follow [`dev/release-new-version-prompt.md`](dev/release-new-version-prompt.md) when preparing a release (notes file, changelog, and format).

### Workflow

At the end of any task that modifies the repo:

1. Review your diff.
2. Add or update bullets in `dev/CHANGELOG.md` under `[Unreleased]`.
3. If you edited an existing bullet for the same change, merge duplicates—do not repeat the same item.

If the user asks you to commit, include `dev/CHANGELOG.md` in the commit when it was updated for that work.

### Example

After adding a upload size validation message in the UI:

```markdown
## [Unreleased]

### Changed
- Clarified upload error when combined file size exceeds the configured limit.
```

After fixing session timeout handling:

```markdown
## [Unreleased]

### Fixed
- Idle sessions now expire correctly after `SESSION_TIMEOUT_SECONDS` without leaving stale review state.
```

## Codebase map — where to change what

This is a **Flask web app** with a shared Python library. There is no frontend build step (plain HTML templates + static JS/CSS). Business logic lives mostly in Python.

```
aegis_keepass_lib.py     ← Aegis decrypt/parse, KeePass I/O, matching, OTP apply
app/
  __init__.py            ← App factory, config, blueprint registration
  session.py             ← In-memory session state and secure wipe lifecycle
  secure.py              ← SecureBytes, spill-to-/tmp encryption, memory wipe
  auth.py                ← Session cookie helpers and route guards
  routes/
    upload.py            ← Upload page + POST /api/upload
    review.py            ← Review UI + match/apply/download/end-session APIs
    health.py            ← GET /health
  templates/             ← Jinja2 HTML (upload.html, review.html, base.html)
  static/js/             ← upload.js, review.js (fetch calls to /api/*)
  static/css/app.css     ← Styles
wsgi.py                  ← Gunicorn entry: create_app()
```

| Task | Primary files |
|------|----------------|
| Aegis backup parsing / decryption | `aegis_keepass_lib.py` (`AegisDecryptor`, `AegisParser`, `AegisEntry`) |
| KeePass open/save / TOTP fields | `aegis_keepass_lib.py` (`KeePassKdbx`, `KeePassUpdater`) |
| Fuzzy matching / re-import by UUID | `aegis_keepass_lib.py` (`EntryMatcher`, `MatchResult`) |
| Upload validation and ingestion | `app/routes/upload.py` |
| Review UI, manual links, download | `app/routes/review.py`, `app/templates/review.html`, `app/static/js/review.js` |
| Upload UI and client-side checks | `app/templates/upload.html`, `app/static/js/upload.js` |
| Session timeout, state, wipe on end | `app/session.py`, `app/secure.py` |
| New HTTP route or API | Relevant blueprint in `app/routes/`, register in `app/__init__.py` if adding a blueprint |
| Config / env defaults | `app/__init__.py`, `docker-compose.yml`, document in `README.md` |
| Version string (footer, releases) | `app/_version.py` only |
| Container image | `Dockerfile`, `.dockerignore` |

### Modifying sources

1. **Read before editing** — match naming, patterns, and error handling in the file you touch.
2. **Keep layers separated**:
   - **Library** (`aegis_keepass_lib.py`) — format-agnostic logic; no Flask imports.
   - **Routes** — HTTP, templates, JSON; delegate heavy work to the library.
   - **Session/secure** — sensitive data lifecycle; use `SecureBytes` and `WipeRegistry` for secrets and file bytes.
3. **Session model** — state is **in-memory per worker**. Run Gunicorn with **`--workers 1`** locally and in Docker. Do not assume shared storage across workers or restarts.
4. **API + UI together** — JSON endpoints under `/api/*` are consumed by `app/static/js/*.js`. When changing request/response shape, update both the route and the matching JS.
5. **Templates** — extend `base.html`; version and GitHub link come from the context processor in `app/__init__.py`.
6. **Dependencies** — add runtime packages to `requirements.txt` and test tools to `requirements-dev.txt`; rebuild Docker (`docker compose up --build`) to pick runtime deps up in containers.
7. **Security-sensitive code** — never log passwords, decrypted vault JSON, or `.kdbx` bytes. Prefer `SecureBytes` over plain `str`/`bytes` for credentials and uploads.

## Development environment

Full setup is in [`dev/DEVEL.md`](dev/DEVEL.md). Minimal flow for agents:

```bash
cd /path/to/aegis-keepass
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Run locally (preferred for fast iteration):

```bash
source .venv/bin/activate
export FLASK_SECRET_KEY=dev-secret   # optional; stabilizes session cookies across restarts
gunicorn --bind 127.0.0.1:8580 --bind '[::1]:8580' --workers 1 --timeout 120 wsgi:app
```

Open [http://127.0.0.1:8580](http://127.0.0.1:8580). Wait until the worker has booted (`Booting worker` in the log, or `/health` returns 200) before loading the UI.

Run in Docker (matches production image):

```bash
docker compose up --build --wait && docker compose logs -f
```

(`--wait` implies detached mode; `logs -f` is what shows the Gunicorn `Listening` / `Booting worker` lines.)

After changing `Dockerfile` or dependencies, rebuild with `--build`. Python-only changes do not require a rebuild when using the venv path.

## Testing changes

Agents must run the checks below after non-trivial edits and report what they ran.

### 1. Automated suite (preferred)

With venv activated and `requirements-dev.txt` installed, from repo root:

```bash
pip install -r requirements.txt -r requirements-dev.txt   # once, or after dep changes
pytest
```

Tests live under `tests/` (unit + Flask integration). Fixtures generate synthetic encrypted Aegis/KeePass data at runtime — do not commit real vaults. Fix failing tests before proceeding.

### 2. Static checks (always)

With venv activated, from repo root:

```bash
python -m compileall -q aegis_keepass_lib.py app wsgi.py
python -c "from app import create_app; create_app(); print('OK')"
```

Fix any syntax or import errors before proceeding.

### 3. Health check (server running)

```bash
curl -sf http://127.0.0.1:8580/health && echo
```

Expect `200`. Use this after starting Gunicorn or Compose.

### 4. Scope-appropriate manual checks

| Area changed | What to verify |
|--------------|----------------|
| Upload route / `upload.js` / `upload.html` | Page loads; invalid files rejected; encrypted Aegis + valid `.kdbx` accepted |
| Review route / `review.js` / matching | Review page shows matches; manual link works; conflicts surfaced |
| `aegis_keepass_lib.py` (matching) | Auto-match quality; `AegisUUID` in Notes respected on re-import |
| `aegis_keepass_lib.py` (KeePass) | Downloaded `.kdbx` opens; `TimeOtp-*` fields present on matched entries |
| Session / secure / auth | **End session** returns to upload; idle timeout behaves if touched |
| Docker / Compose | `docker compose up --build` succeeds; `docker compose ps` shows healthy |
| Templates / CSS only | Visual check in browser; no broken layout or JS console errors |

Full end-to-end smoke (when touching core flow):

1. Start app (venv or Docker).
2. Upload **copies** of an encrypted Aegis `.json` and a `.kdbx` (never commit real files).
3. Complete review; download merged database.
4. Confirm session ends cleanly.

Use **copies** of real backups only on localhost. Do not add sample vaults to the repo.

### 5. When tests are not runnable

If you cannot run `pytest` or the app (missing deps, Docker, etc.), say so explicitly and list what you verified statically. Do not claim end-to-end verification without evidence.

## Other project docs

| File | Purpose |
|------|---------|
| [`dev/DEVEL.md`](dev/DEVEL.md) | Development setup, build, test, and release |
| [`dev/release-new-version-prompt.md`](dev/release-new-version-prompt.md) | Step-by-step prompt for preparing a new release |
| [`dev/CHANGELOG.md`](dev/CHANGELOG.md) | Change history (maintained by agents and developers) |
| [`README.md`](README.md) | User-facing overview and quick start |
| [`app/_version.py`](app/_version.py) | Single source of truth for release version |

## General principles

- **Minimize scope** — only change what the task requires.
- **Match existing conventions** — read surrounding code before editing.
- **No inline imports** — keep imports at the top of Python modules.
- **Security** — this app handles encrypted backups and passwords in memory; never commit real credentials or customer data.
