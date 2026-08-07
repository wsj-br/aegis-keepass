# Desktop packaging

Builds a standalone desktop executable that embeds the Flask UI in a native
window via [pywebview](https://pywebview.flowrl.com/), served by Waitress on
loopback. Docker remains the primary distribution channel; these builds are an
optional no-Docker path.

## Prerequisites

Install runtime deps from the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-desktop.txt
```

### Platform system packages

| OS | Extra requirement |
|----|-------------------|
| **Linux** | WebKitGTK — e.g. `sudo apt-get install -y gir1.2-webkit2-4.1 gir1.2-gtk-3.0 libwebkit2gtk-4.1-dev`. End users also need the runtime WebKitGTK package. |
| **Windows** | [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (preinstalled on most Windows 10/11 systems). |
| **macOS** | No extra packages; pywebview uses WKWebView. For a universal2 binary, use a universal2 CPython (GitHub Actions `setup-python` with `architecture: universal2`). |

## Local build

```bash
./packaging/build-desktop.sh
```

Or manually:

```bash
pyinstaller --noconfirm --clean packaging/aegis-keepass.spec
```

Output is under `dist/`:

- Linux/Windows: `dist/aegis-keepass` (or `aegis-keepass.exe`)
- macOS: `dist/Aegis-KeePass OTP Sync.app` and/or `dist/aegis-keepass`

## Dev run without packaging

```bash
export AK_DESKTOP=1   # set automatically by desktop_main.py
python desktop_main.py
```

## Release artifacts (CI)

`.github/workflows/desktop-release.yml` builds and uploads:

| Artifact | Runner |
|----------|--------|
| `aegis-keepass-<ver>-windows-x64.zip` | `windows-latest` |
| `aegis-keepass-<ver>-linux-x64.tar.gz` | `ubuntu-latest` |
| `aegis-keepass-<ver>-linux-arm64.tar.gz` | `ubuntu-24.04-arm` |
| `aegis-keepass-<ver>-macos-universal2.zip` | `macos-14` |

These are attached to the GitHub Release by the workflow (independent of
`scripts/release.sh`, which still attaches the Docker start scripts).
