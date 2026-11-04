# Desktop packaging

The desktop app embeds the Flask UI in a native window via [pywebview](https://pywebview.flowrl.com/), served by Waitress on loopback. GitHub Releases are the install path. See the [README](../README.md) for the download table.

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
| **Linux** | GTK 3 + WebKitGTK + GObject introspection typelibs (and their ICU deps). The PyInstaller binary bundles the PyGObject (`gi`) Python module and does **not** bundle GTK/ICU libraries, typelibs, or icon themes. |
| **Windows** | [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (preinstalled on most Windows 10/11 systems). |
| **macOS** | No extra packages; pywebview uses WKWebView. The build matches the Mac it is built on (Intel or Apple Silicon) and is wrapped in a DMG. |

**Linux — run a packaged binary** (Debian/Ubuntu):

```bash
sudo apt-get install -y \
  gir1.2-gtk-3.0 \
  gir1.2-webkit2-4.1 \
  libgtk-3-0 \
  libwebkit2gtk-4.1-0
```

**Linux — build or `./scripts/dev`** (PyGObject for the same Python):

```bash
sudo apt-get install -y \
  gir1.2-gtk-3.0 \
  gir1.2-webkit2-4.1 \
  libwebkit2gtk-4.1-dev \
  pkg-config \
  python3-gi
```

`python3-gi` installs into the distro interpreter (`/usr/lib/python3/dist-packages`), which a normal venv does not see. The desktop entrypoint and the PyInstaller spec pick up that `gi` package when its ABI matches the venv (typical local `python3 -m venv`). If it does not match — for example CI's Python 3.13 on Ubuntu 24.04, whose `python3-gi` is built for 3.12 — install PyGObject into that environment instead:

```bash
pip install 'PyGObject>=3.48,<3.52'
```

That pin stays on girepository-1.0. Building it from source also needs `libgirepository1.0-dev`, `libcairo2-dev`, and `gobject-introspection`.

## Local build

```bash
./scripts/build-desktop.sh
```

PyInstaller may print benign “Hidden import … not found” lines for optional deps (`pycparser.lextab` / `yacctab` with pycparser 3.x, and `gi._gi_cairo` if Cairo GI bindings are not installed). They do not block the build.

The Linux build strips bundled `share/icons` / locales / themes and GTK/ICU/WebKit shared libraries so the artifact stays smaller; those come from the host packages listed above.

Output is under `dist/`:

- Linux/Windows: `dist/aegis-keepass` (or `aegis-keepass.exe`)
- macOS: `dist/Aegis-KeePass OTP Sync.app`, plus `dist/aegis-keepass-<ver>-macos-arm64.dmg` or `macos-intel.dmg` and a `.dmg.sha256` file

The disk image uses `dmgbuild` 1.6.5 (installed into `build/dmg-py` on first use, not the project venv). It opens with the app on the left, an arrow, and an Applications shortcut on the right. A DMG can only be built on macOS.

## Dev run without packaging

```bash
./scripts/dev
```

That opens the native window. For a browser on loopback instead (no window):

```bash
./scripts/dev --http
```

Then open [http://127.0.0.1:8580](http://127.0.0.1:8580). `./scripts/dev` uses `.venv` when that directory exists.

## Release artifacts (CI)

[`.github/workflows/desktop-release.yml`](../.github/workflows/desktop-release.yml) builds on native runners and uploads:

| Artifact | Runner |
|----------|--------|
| `aegis-keepass-<ver>-windows-x64.zip` | `windows-latest` |
| `aegis-keepass-<ver>-windows-arm64.zip` | `windows-11-arm` |
| `aegis-keepass-<ver>-linux-amd64.tar.gz` | `ubuntu-latest` |
| `aegis-keepass-<ver>-linux-arm64.tar.gz` | `ubuntu-24.04-arm` |
| `aegis-keepass-<ver>-macos-intel.dmg` (+ `.sha256`) | `macos-15-intel` |
| `aegis-keepass-<ver>-macos-arm64.dmg` (+ `.sha256`) | `macos-15` |

`scripts/release.sh` publishes the GitHub Release. The workflow attaches these files afterward. Linux and Windows archives include `LICENSE` and `NOTICES` beside the binary. On macOS those files are inside the `.app`.
