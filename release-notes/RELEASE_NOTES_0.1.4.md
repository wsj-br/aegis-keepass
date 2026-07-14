# Release 0.1.4

GPL-3.0 license text and automated third-party notices generation.

## Highlights

- **LICENSE** — Repo root now includes the full GPL-3.0 license text.
- **NOTICES tooling** — `scripts/update-notices.sh` regenerates the root `NOTICES` file from `requirements.txt` via `pip-licenses`.

## Changes

### Added
- `scripts/update-notices.sh` regenerates the repo-root `NOTICES` file from `requirements.txt` via `pip-licenses`.
- Added a `LICENSE` file to the repo root for the GPL-3.0 license text.

---

## Provided start scripts to run the tool locally

| OS                                    | Script                         |
|---------------------------------------|--------------------------------|
| Windows (PowerShell) + Docker Desktop | `aegis-keepass-start.ps1`      |
| Windows (PowerShell) + WSL Containers | `aegis-keepass-start-wslc.ps1` |
| Linux (Bash)                          | `aegis-keepass-start.sh`       |


See [README.md](https://github.com/wsj-br/aegis-keepass/blob/main/README.md) for more details.