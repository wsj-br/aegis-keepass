# Aegis-KeePass OTP Sync

Import TOTP secrets from [Aegis Authenticator](https://getaegis.app/) encrypted backups into [KeePass](https://keepass.info/) entries. Upload your files in the browser, review matches, and download a merged `.kdbx` database—no plaintext XML export required.

## Overview

This tool connects Aegis (mobile authenticator) and KeePass (password manager) by:

- **Importing** OTP secrets from encrypted Aegis backups (decrypted only in server memory)
- **Opening** your KeePass `.kdbx` database directly
- **Matching** Aegis entries to KeePass entries using fuzzy string matching
- **Applying** native KeePass TOTP fields (`TimeOtp-Secret-Base32`, and related settings)
- **Exporting** a merged, encrypted `.kdbx` file for download
- **Recording** Aegis UUID markers in KeePass Notes to support future re-imports

Designed for single-user, localhost use. All processing happens in your browser session; nothing is persisted on the server after download or session end.

## Quick start

**Requirements:** Docker and Docker Compose.

```bash
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080). Stop the container with `Ctrl+C` or `docker compose down`.

### Workflow

1. **Upload** — Select your encrypted Aegis backup (`.json`) and KeePass database (`.kdbx`). Enter the Aegis backup password, KeePass master password, and keyfile if your database uses one.
2. **Review** — Confirm automatic matches, manually link unmatched entries, and resolve conflicts before applying changes.
3. **Download** — Click **Download merged database** to receive `keepass-merged.kdbx` in your browser.

After download or **End session**, all session data is securely wiped from server memory.

**Important:** Back up your original KeePass database before replacing it with the downloaded file.

## Requirements

| Input | Format | Notes |
|-------|--------|-------|
| Aegis backup | Encrypted `.json` | Export from Aegis with encryption enabled; plain JSON backups are not supported |
| KeePass database | `.kdbx` | From KeePass 2.x, KeePassXC, or compatible clients |
| KeePass keyfile | Optional | Required only if your database uses a keyfile in addition to the master password |

## Project structure

| Path | Purpose |
|------|---------|
| `app/` | Flask web application (upload, review, session APIs) |
| `aegis_keepass_lib.py` | Parsing, decryption, matching, and KeePass database updates |
| `wsgi.py` | Gunicorn application entry point |
| `Dockerfile` | Container image (Python 3.12, non-root user) |
| `docker-compose.yml` | Local deployment on `127.0.0.1:8080` |
| `app/_version.py` | Application version (single source of truth) |
| `scripts/release.sh` | Create GitHub release and trigger Docker CI |

## Configuration

Environment variables can be set in `docker-compose.yml` or passed to Gunicorn when running locally.

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_TIMEOUT_SECONDS` | `1800` | Idle session timeout in seconds (30 minutes) |
| `MAX_IN_MEMORY_UPLOAD_BYTES` | `33554432` | Combined upload size kept entirely in RAM (32 MB) |
| `MAX_UPLOAD_BYTES` | `52428800` | Maximum allowed upload size (50 MB) |
| `FLASK_SECRET_KEY` | *(random per start)* | Secret used to sign session cookies. Set explicitly if you need stable sessions across restarts (e.g. during development) |

The Docker Compose file also configures:

- **Read-only root filesystem** — the container cannot write outside `/tmp`
- **Tmpfs for `/tmp`** — temporary spill storage for large uploads (64 MB), cleared when the container stops

## How matching works

Matching uses [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) against KeePass entry titles:

1. Build an Aegis identifier from `issuer` and `name`
2. Score against each KeePass entry title
3. Boost scores using issuer/name substrings, extracted domains, usernames, and numeric tokens
4. Prefer existing `AegisUUID` markers in KeePass Notes when re-importing
5. Flag conflicts when one KeePass entry matches multiple Aegis entries

Entries that do not match automatically can be linked manually in the review step.

## Re-import tracking

Each matched KeePass entry receives an `AegisUUID` marker in its Notes field:

```
Existing notes...

AegisUUID: 00000000-0000-4000-8000-000000000001
```

This enables reliable re-imports: the tool recognises previously linked entries by UUID rather than relying on title matching alone.

## OTP fields written to KeePass

| Field | Description |
|-------|-------------|
| `TimeOtp-Secret-Base32` | TOTP shared secret (Base32) |
| `TimeOtp-Period` | Time step in seconds |
| `TimeOtp-Digits` | Number of OTP digits |
| `TimeOtp-Algorithm` | Hash algorithm (e.g. `HMAC-SHA-1`) |

These are KeePass 2.x native TOTP fields, compatible with KeePassXC and Keepass2Android.

## Security model

- **Encrypted at rest on your machine** — You upload already-encrypted Aegis JSON and `.kdbx` files; decryption happens only in server memory during the session
- **In-memory processing** — Typical backups are held in wipeable buffers and never written to disk
- **Secure wipe on session end** — Sensitive buffers are overwritten with random data, then zeroed, when you download or end the session
- **No server-side retention** — The merged database is streamed to your browser; the server does not keep a copy
- **Localhost-only host binding (with provided Compose file)** — Gunicorn listens on `0.0.0.0:8080` inside the container (normal for Docker port forwarding). The included `docker-compose.yml` maps that to **`127.0.0.1:8080` on the host**, so other machines cannot reach the app unless you change the port mapping (e.g. to `8080:8080`)
- **Hardened container** — Non-root user, read-only filesystem, tmpfs for temporary files
- **Session cookies** — HttpOnly and SameSite=Strict; there is no login layer (intended for trusted localhost use)
- **Health check** — `GET /health` returns `200 OK` for container orchestration

### Limitations

Memory wiping is best-effort. Python `str` and immutable `bytes` objects cannot be guaranteed erased; the app uses wipeable `SecureBytes` buffers where possible. CPython may copy data internally during cryptography or HTTP handling. This tool is suitable for personal localhost use, not for environments that require hardware security modules or formal secret-management guarantees.

Uploads exceeding the in-memory threshold (>32 MB combined) are encrypted and written to `/tmp` inside the container. Those files are shredded when the session ends.

## Development

**Requirements:** Python 3.12+ (matches the Docker image).

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
gunicorn --bind 127.0.0.1:8080 --workers 1 --timeout 120 wsgi:app
```

Open [http://localhost:8080](http://localhost:8080). Use a single worker so in-memory session state stays consistent.

## Releasing

Version is defined in [`app/_version.py`](app/_version.py). Tag conventions:

| Layer | Format | Example |
|-------|--------|---------|
| Git tag / GitHub Release | `vX.Y.Z` | `v0.1.0` |
| Docker image tag | `X.Y.Z` | `0.1.0` |
| `app/_version.py` / UI footer | `X.Y.Z` | `0.1.0` |

To publish a release:

1. Bump `__version__` in `app/_version.py`
2. Write `release-notes/RELEASE_NOTES_<version>.md`
3. Commit the changes
4. Run `./scripts/release.sh` (use `--dry-run` first to validate)

The script creates a GitHub Release (`vX.Y.Z`), which triggers CI to build and publish multi-arch Docker images to `ghcr.io/wsj-br/aegis-keepass`.

### Pull published image

```bash
docker pull ghcr.io/wsj-br/aegis-keepass:latest
docker run --rm -p 127.0.0.1:8080:8080 ghcr.io/wsj-br/aegis-keepass:latest
```

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| Upload rejected | Confirm the Aegis file is an **encrypted** backup and the KeePass file is a valid `.kdbx`. Check file sizes against `MAX_UPLOAD_BYTES`. |
| Wrong password | Aegis and KeePass passwords are validated at upload; re-upload with the correct credentials. |
| Unmatched entries | Use manual linking in the review step. Matching depends on title similarity—rename entries in KeePass or Aegis if titles differ significantly. |
| Session expired | Idle sessions time out after 30 minutes by default. Start again from the upload page. |
| Port already in use | Stop any process on port 8080, or change the host port mapping in `docker-compose.yml`. |

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

## License

Licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html). Copyright (c) 2026 Waldemar Scudeller Jr.
