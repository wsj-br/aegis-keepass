# Release 0.1.3

Smaller Alpine-based image, default port 8580, and attested multi-arch releases.

## Highlights

- **Alpine image base** — Docker image now builds on `python:3.13-alpine` instead of Debian slim, for a smaller OS surface and fewer reported CVEs.
- **Default port 8580** — Dockerfile, Compose, start scripts, and docs listen on `8580` instead of `8080`.
- **Provenance and SBOM** — Release workflow attaches SLSA provenance (`mode=max`) and an SPDX SBOM to multi-arch GHCR images.

## Docker

```bash
docker pull ghcr.io/wsj-br/aegis-keepass:0.1.3
docker run --rm -p 127.0.0.1:8580:8580 ghcr.io/wsj-br/aegis-keepass:0.1.3
```

Open [http://localhost:8580](http://localhost:8580).

Start scripts are also attached as downloadable assets on the [GitHub Release](https://github.com/wsj-br/aegis-keepass/releases/tag/v0.1.3).

## Changes

### Changed
- Default listen/host port changed from `8080` to `8580` (Dockerfile, Compose, start scripts, and docs).
- Docker image base switched from `python:3.12-slim` (Debian) to `python:3.13-alpine` for a smaller OS surface and fewer reported CVEs.
- Release workflow now emits SLSA provenance (`mode=max`) and an SPDX SBOM on multi-arch GHCR images.

### Added
- `dev/DEVEL.md` notes for Alpine / Python 3.13 image base, Docker Scout attestation expectations, and why the copyleft policy may still flag the image (`pykeepass` GPL-3.0 and Alpine GPL components).
