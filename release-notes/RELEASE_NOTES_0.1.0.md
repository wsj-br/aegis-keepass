# Release 0.1.0

First public release of Aegis-KeePass OTP Sync.

## Highlights

- Import TOTP secrets from encrypted Aegis Authenticator backups into KeePass `.kdbx` databases
- Fuzzy matching with manual review and conflict resolution
- Flask web UI for upload, review, and download workflow
- Docker image with hardened defaults (non-root user, read-only filesystem, tmpfs for `/tmp`)
- Multi-arch Docker images published to GHCR (`linux/amd64` and `linux/arm64`)

## Docker

```bash
docker pull ghcr.io/wsj-br/aegis-keepass:0.1.0
docker run --rm -p 127.0.0.1:8080:8080 ghcr.io/wsj-br/aegis-keepass:0.1.0
```

Open [http://localhost:8080](http://localhost:8080).
