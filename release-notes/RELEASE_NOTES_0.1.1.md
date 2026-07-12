# Release 0.1.1

Performance improvements for large KeePass vaults, a clearer post-download completion screen, and developer documentation.

## Highlights

- **Faster large-vault loading** — Opening big KeePass databases is much quicker; entry metadata is collected in a single pass instead of repeated tree scans per entry.
- **Download completion screen** — After saving the merged database, the review page shows a summary (total entries, OTP coverage, updated and cleaned counts) and an **End session** button instead of redirecting immediately to upload.
- **Longer Docker timeout** — Gunicorn request timeout increased to 300s so slow hosts can finish unlocking and loading large databases.
- **Developer docs** — Added `dev/DEVEL.md` (local setup, smoke tests, release checklist) and `AGENT.md` (changelog conventions for contributors).

## Docker

```bash
docker pull ghcr.io/wsj-br/aegis-keepass:0.1.1
docker run --rm -p 127.0.0.1:8080:8080 ghcr.io/wsj-br/aegis-keepass:0.1.1
```

Open [http://localhost:8080](http://localhost:8080).

## Changes

### Added
- Developer guide at `dev/DEVEL.md` (environment setup, build, test, release).
- Agent instructions at `AGENT.md` requiring changelog updates for meaningful changes.
- Step 3 download completion view after saving the merged database: header advances to Download, with a summary of total KeePass entries, entries with OTP, updated count, and cleaned count, plus an End session button; the review toolbar and entry table are hidden on this screen.

### Fixed
- Slow KeePass database opening on large vaults: `entries_from_db` no longer runs repeated pykeepass XPath tree scans per entry (recycle-bin lookup, group path, and string fields are read in a single pass via lxml ancestor traversal).

### Changed
- After download, the review page shows the completion summary instead of auto-redirecting to upload; the user returns to upload only when they click End session.
- Gunicorn worker request timeout increased from 120s to 300s in `Dockerfile` to accommodate large-database unlock and load on slow hosts.
