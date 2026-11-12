# Release 0.2.3

Linux AppImages open on more desktops, including systems where a bundled library kept the window from starting.

## Highlights

- **Linux startup** — AppImages no longer include `liblcms2`, which could replace the system's WebKitGTK library and stop the window from opening. The AMD64 build is produced on Ubuntu 22.04 so it stays compatible with that desktop. Both Linux builds check that the packaged app reaches the upload page before they are published.
- **Linux desktop shortcut** — An AppImage path that contains spaces is quoted correctly. If your app manager already created a desktop entry, that entry is left in place. The shortcut records this application version.

For the complete list of changes, see [`dev/CHANGELOG.md`](../dev/CHANGELOG.md).

## Install

Download the build for your computer from the [GitHub Release](https://github.com/wsj-br/aegis-keepass/releases/tag/v0.2.3):

- Linux AMD64: `aegis-keepass-0.2.3-linux-amd64.AppImage`
- Linux ARM64: `aegis-keepass-0.2.3-linux-arm64.AppImage`
- macOS Intel: `aegis-keepass-0.2.3-macos-intel.dmg`
- macOS Apple Silicon: `aegis-keepass-0.2.3-macos-arm64.dmg`
- Windows x64: `aegis-keepass-0.2.3-windows-x64.exe`
- Windows ARM: `aegis-keepass-0.2.3-windows-arm64.exe`

**Linux.** Mark the AppImage executable and run it. A current Ubuntu, Debian, or Zorin OS desktop already includes GTK 3 and WebKitGTK 4.1.

```bash
chmod +x aegis-keepass-0.2.3-linux-amd64.AppImage
./aegis-keepass-0.2.3-linux-amd64.AppImage
```

If the window does not open and the terminal mentions WebKit or `gi`, install WebKitGTK 4.1 (typical of Ubuntu 22.04 and Zorin OS 17):

```bash
sudo apt-get install -y gir1.2-gtk-3.0 gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0
```

Use the `linux-arm64` AppImage on ARM. Other distributions need the same GTK 3 and WebKitGTK 4.1 libraries under their own package names. `LICENSE` and `NOTICES` are inside the image.

**macOS.** Open the disk image and drag **Aegis-KeePass OTP Sync** to Applications. The build is unsigned. The first time you launch it, right-click the app, choose **Open**, then choose **Open Anyway** under **System Settings → Privacy & Security** if Gatekeeper still blocks it. Each DMG is published with a `.dmg.sha256` file.

**Windows.** Run the installer. It installs for the current user and adds a Start menu shortcut. [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) is required and is already installed on most Windows 10 and 11 systems. The file is unsigned, so SmartScreen may need **More info**, then **Run anyway**. The x64 installer only runs on Intel or AMD PCs, and the ARM installer only runs on Windows ARM.
