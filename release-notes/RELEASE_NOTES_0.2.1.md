# Release 0.2.1

The desktop app is now the product. Docker and the container start scripts are gone; you download a build for your computer and save the merged database with a native file dialog.

## Highlights

- **Desktop app only** — Open the window, read an encrypted Aegis backup and a KeePass database, review matches, and save a merged `.kdbx`. There is no Docker image or Compose file.
- **Six native downloads** — Linux AMD64 and ARM64 AppImages, macOS Intel and Apple Silicon disk images (plus a `.sha256` file), and Windows x64 and ARM installers.
- **Native Save dialog** — Choosing where to write the merged database uses the system save dialog.
- **Compact window** — Default size is 750×660. Upload and review fit the window; the match table scrolls. Step labels in the app are **Read** and **Save**.
- **App logo** — The window, Windows and macOS packages, and the Linux desktop entry use the vault-shield logo.
- **System theme** — Follows the host appearance, including Windows dark mode. The toggle cycles System → Light → Dark.
- **Linux AppImage** — One file per CPU. A current Ubuntu, Debian, or Zorin OS desktop already has GTK 3 and WebKitGTK 4.1.

For the complete list of changes, see [`dev/CHANGELOG.md`](../dev/CHANGELOG.md).

## Install

Download the build for your computer from the [GitHub Release](https://github.com/wsj-br/aegis-keepass/releases/tag/v0.2.1):

- Linux AMD64: `aegis-keepass-0.2.1-linux-amd64.AppImage`
- Linux ARM64: `aegis-keepass-0.2.1-linux-arm64.AppImage`
- macOS Intel: `aegis-keepass-0.2.1-macos-intel.dmg`
- macOS Apple Silicon: `aegis-keepass-0.2.1-macos-arm64.dmg`
- Windows x64: `aegis-keepass-0.2.1-windows-x64.exe`
- Windows ARM: `aegis-keepass-0.2.1-windows-arm64.exe`

**Linux.** Mark the AppImage executable and run it. A current Ubuntu, Debian, or Zorin OS desktop already includes GTK 3 and WebKitGTK 4.1.

```bash
chmod +x aegis-keepass-0.2.1-linux-amd64.AppImage
./aegis-keepass-0.2.1-linux-amd64.AppImage
```

If the window does not open and the terminal mentions WebKit or `gi`, install WebKitGTK 4.1 (typical of Ubuntu 22.04 and Zorin OS 17):

```bash
sudo apt-get install -y gir1.2-gtk-3.0 gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0
```

Use the `linux-arm64` AppImage on ARM. Other distributions need the same GTK 3 and WebKitGTK 4.1 libraries under their own package names. `LICENSE` and `NOTICES` are inside the image.

**macOS.** Open the disk image and drag **Aegis-KeePass OTP Sync** to Applications. The build is unsigned. The first time you launch it, right-click the app, choose **Open**, then choose **Open Anyway** under **System Settings → Privacy & Security** if Gatekeeper still blocks it. Each DMG is published with a `.sha256` file.

**Windows.** Run the installer. It installs for the current user and adds a Start menu shortcut. [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) is required and is already installed on most Windows 10 and 11 systems. The file is unsigned, so SmartScreen may need **More info**, then **Run anyway**. The x64 installer only runs on Intel or AMD PCs, and the ARM installer only runs on Windows ARM.
