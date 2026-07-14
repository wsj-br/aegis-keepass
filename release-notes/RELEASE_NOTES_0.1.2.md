# Release 0.1.2

One-command start scripts for Linux, macOS, Docker Desktop, and WSL Containers.

## Highlights

- **One-command start scripts** — Pull and run the published image with `aegis-keepass-start.sh` (Linux/macOS), `aegis-keepass-start.ps1` (Docker Desktop), or `aegis-keepass-start-wslc.ps1` (WSL Containers / `wslc`), bound to localhost on port 8580.
- **Release assets** — The three start scripts are attached to each GitHub Release for direct download from `releases/latest/download/...`.

## Docker

```bash
docker pull ghcr.io/wsj-br/aegis-keepass:0.1.2
docker run --rm -p 127.0.0.1:8580:8580 ghcr.io/wsj-br/aegis-keepass:0.1.2
```

Open [http://localhost:8580](http://localhost:8580).

Start scripts are also attached as downloadable assets on the [GitHub Release](https://github.com/wsj-br/aegis-keepass/releases/tag/v0.1.2).

## Changes

### Added
- One-command container start scripts at repo root: `aegis-keepass-start.sh` (Linux/macOS), `aegis-keepass-start.ps1` (Docker Desktop), and `aegis-keepass-start-wslc.ps1` (WSL Containers / `wslc`).
- `scripts/release.sh` attaches the three start scripts as GitHub Release assets (`releases/latest/download/...`).
