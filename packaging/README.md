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
| **Linux** | GTK 3 and WebKitGTK 4.1 from the host. A current Ubuntu, Debian, or Zorin OS desktop already has them. The image bundles the PyGObject (`gi`) Python module and does **not** bundle GTK/ICU libraries, typelibs, or icon themes. |
| **Windows** | [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (preinstalled on most Windows 10/11 systems). The release file is an Inno Setup installer, not a zip. |
| **macOS** | No extra packages; pywebview uses WKWebView. The build matches the Mac it is built on (Intel or Apple Silicon) and is wrapped in a DMG. |

**Linux — run a packaged binary** (Debian/Ubuntu/Zorin):

A current desktop already has GTK 3 and WebKitGTK 4.1.

Ubuntu 22.04 and Zorin OS 17 have WebKitGTK 4.0, so install 4.1 before the window will open:

```bash
sudo apt-get install -y gir1.2-gtk-3.0 gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0
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

- Linux: `dist/aegis-keepass` and `dist/aegis-keepass-<ver>-linux-amd64.AppImage` or `linux-arm64.AppImage` (`scripts/package-linux-appimage.sh`, using appimagetool 1.9.1)
- Windows: `dist/aegis-keepass.exe` and `dist/aegis-keepass-<ver>-windows-x64.exe` or `windows-arm64.exe` (`scripts/package-windows-installer.ps1`, using the 64-bit Inno Setup 7.1.1 compiler)
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
| `aegis-keepass-<ver>-windows-x64.exe` | `windows-latest` |
| `aegis-keepass-<ver>-windows-arm64.exe` | `windows-11-arm` |
| `aegis-keepass-<ver>-linux-amd64.AppImage` | `ubuntu-latest` |
| `aegis-keepass-<ver>-linux-arm64.AppImage` | `ubuntu-24.04-arm` |
| `aegis-keepass-<ver>-macos-intel.dmg` (+ `.sha256`) | `macos-15-intel` |
| `aegis-keepass-<ver>-macos-arm64.dmg` (+ `.sha256`) | `macos-15` |

`scripts/release.sh` publishes the GitHub Release. The workflow attaches these files afterward. The Linux AppImage includes `LICENSE` and `NOTICES` under `usr/share/doc/aegis-keepass/`. The Windows installer copies those files next to `aegis-keepass.exe` and adds a Start menu shortcut for the current user. On macOS they are inside the `.app`. Windows installers are built with the 64-bit [Inno Setup](https://jrsoftware.org/isinfo.php) 7.1.1 compiler so the same script runs on the x64 and ARM runners.
