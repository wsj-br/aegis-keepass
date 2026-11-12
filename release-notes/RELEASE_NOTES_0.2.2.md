# Release 0.2.2

Windows desktop builds are published again, including Windows on ARM.

## Highlights

- **Windows installers are built again** — The x64 and ARM installers failed in the previous release workflow. Both are produced for this tag.
- **Windows on ARM** — That build uses a `cryptography` release that still ships a native ARM wheel, so the installer can be built on the Windows ARM runner.
- **Other platforms** — Linux, macOS, and Windows x64 builds use `cryptography` 50 or newer.

For the complete list of changes, see [`dev/CHANGELOG.md`](../dev/CHANGELOG.md).

## Install

Download the build for your computer from the [GitHub Release](https://github.com/wsj-br/aegis-keepass/releases/tag/v0.2.2):

- Linux AMD64: `aegis-keepass-0.2.2-linux-amd64.AppImage`
- Linux ARM64: `aegis-keepass-0.2.2-linux-arm64.AppImage`
- macOS Intel: `aegis-keepass-0.2.2-macos-intel.dmg`
- macOS Apple Silicon: `aegis-keepass-0.2.2-macos-arm64.dmg`
- Windows x64: `aegis-keepass-0.2.2-windows-x64.exe`
- Windows ARM: `aegis-keepass-0.2.2-windows-arm64.exe`

**Linux.** Mark the AppImage executable and run it. A current Ubuntu, Debian, or Zorin OS desktop already includes GTK 3 and WebKitGTK 4.1.

```bash
chmod +x aegis-keepass-0.2.2-linux-amd64.AppImage
./aegis-keepass-0.2.2-linux-amd64.AppImage
```

If the window does not open and the terminal mentions WebKit or `gi`, install WebKitGTK 4.1 (typical of Ubuntu 22.04 and Zorin OS 17):

```bash
sudo apt-get install -y gir1.2-gtk-3.0 gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0
```

Use the `linux-arm64` AppImage on ARM. Other distributions need the same GTK 3 and WebKitGTK 4.1 libraries under their own package names. `LICENSE` and `NOTICES` are inside the image.

**macOS.** Open the disk image and drag **Aegis-KeePass OTP Sync** to Applications. The build is unsigned. The first time you launch it, right-click the app, choose **Open**, then choose **Open Anyway** under **System Settings → Privacy & Security** if Gatekeeper still blocks it. Each DMG is published with a `.dmg.sha256` file.

**Windows.** Run the installer. It installs for the current user and adds a Start menu shortcut. [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) is required and is already installed on most Windows 10 and 11 systems. The file is unsigned, so SmartScreen may need **More info**, then **Run anyway**. The x64 installer only runs on Intel or AMD PCs, and the ARM installer only runs on Windows ARM.
