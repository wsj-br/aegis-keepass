Create a new release notes file `release-notes/RELEASE_NOTES_<version>.md` for **Aegis-KeePass OTP Sync** using the instructions below. This will be used by `./scripts/release.sh` as part of the GitHub release process (which triggers desktop builds for Linux AMD64, Linux ARM64, macOS Intel, macOS Apple Silicon, Windows x64, and Windows ARM).

This product is **desktop only**. Do not mention Docker, Compose, containers, or a browser-hosted install.

**Instructions:**

1. **Read `app/_version.py`** (or run `./scripts/version`) to get the current version number (`x.y.z` from `__version__`). If you are preparing notes for a release that is not yet bumped, use the target version you will set with `./scripts/version X.Y.Z`.
2. **Open `dev/CHANGELOG.md`**.
3. **Read the entries under the `## [Unreleased]` section** up to (but not including) the next `## [` heading so you can pick the highlights. Do not copy them into the notes file — the notes link to the changelog for the detailed list.
4. **Format the new file** like the example below. Section order is fixed:
   1. Title and one-sentence summary
   2. `## Highlights`
   3. `## Install` — **the last section in the file**

   Nothing comes after `## Install`. Download filenames and how to install each desktop app stay at the bottom of the notes, after the highlights.

   - Title: `# Release <version>` (e.g. `# Release 0.2.1`)
   - Opening line: one sentence describing what this release is (for the first release, “First public release…”; for later releases, a short summary of the theme).
   - `## Highlights` — Summarize the most important user-facing changes from the changelog bullets (focus on features, fixes, and major improvements; don't list every change verbatim—write clear, user-focused summaries). End the section with one line that points readers to `dev/CHANGELOG.md` for the complete list of changes.
   - `## Install` — **Last section.** Keep the same structure every release (substitute the version in filenames and the release URL):
     - One line that points at the GitHub Release for this tag (`https://github.com/wsj-br/aegis-keepass/releases/tag/v<version>`).
     - The six desktop assets, named exactly:
     - Linux AMD64: `aegis-keepass-<version>-linux-amd64.AppImage`
     - Linux ARM64: `aegis-keepass-<version>-linux-arm64.AppImage`
     - macOS Intel: `aegis-keepass-<version>-macos-intel.dmg`
     - macOS Apple Silicon: `aegis-keepass-<version>-macos-arm64.dmg`
     - Windows x64: `aegis-keepass-<version>-windows-x64.exe`
     - Windows ARM: `aegis-keepass-<version>-windows-arm64.exe`
     - **Linux.** AppImage, not an archive. Do not tell every desktop to install GTK or WebKit first. A current Ubuntu, Debian, or Zorin OS desktop already includes GTK 3 and WebKitGTK 4.1. The first steps are `chmod +x` and run. If the window does not open and the terminal mentions WebKit or `gi`, show `sudo apt-get install -y gir1.2-gtk-3.0 gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0` and note that this is typical of Ubuntu 22.04 and Zorin OS 17. Do not list `libgtk-3-0`; on Ubuntu 24.04 that name does not exist (`libgtk-3-0t64` is already installed with the desktop). Say to use the `linux-arm64` AppImage on ARM. `LICENSE` and `NOTICES` are inside the image.
     - **macOS.** Open the disk image and drag **Aegis-KeePass OTP Sync** to Applications. The build is unsigned: right-click **Open** the first time, then **Open Anyway** under **System Settings → Privacy & Security** if Gatekeeper still blocks it. Each DMG is published with a `.dmg.sha256` file.
     - **Windows.** Run the `.exe` installer (not a zip). It installs for the current user and adds a Start menu shortcut. Link [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) and note it is already installed on most Windows 10 and 11 systems. State both of these sentences: the file is unsigned, so SmartScreen may need **More info**, then **Run anyway**; the x64 installer only runs on Intel or AMD PCs, and the ARM installer only runs on Windows ARM.
   - Don't add Docker, Compose, or container steps anywhere in the file.
5. **Update `dev/CHANGELOG.md`**:
   - Move all lines from `[Unreleased]` to a new section with the current version and today's date (`## [x.y.z] - YYYY-MM-DD`).
   - Leave an empty `[Unreleased]` section at the top for future work.

**Prerequisites (confirm before finishing):**

- `app/_version.py` has `__version__ = "<version>"` matching the notes filename (`./scripts/version` prints that version).
- `release-notes/RELEASE_NOTES_<version>.md` exists and follows this format: `## Highlights` (with the closing line linking to `dev/CHANGELOG.md` for details) and `## Install` as the last section, including the six desktop assets plus Linux, macOS, and Windows install steps.
- Changes are committed on a clean tree before running `./scripts/release.sh` (use `--dry-run` first).

**Example format for the file** (tilde fence so the Linux command block stays inside the example):

~~~~markdown
# Release 0.2.1

Short summary of what this release is.

## Highlights

- Briefly state the most important new features, fixes, or improvements.
- Focus on what people using the desktop app will notice.

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

**macOS.** Open the disk image and drag **Aegis-KeePass OTP Sync** to Applications. The build is unsigned. The first time you launch it, right-click the app, choose **Open**, then choose **Open Anyway** under **System Settings → Privacy & Security** if Gatekeeper still blocks it. Each DMG is published with a `.dmg.sha256` file.

**Windows.** Run the installer. It installs for the current user and adds a Start menu shortcut. [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) is required and is already installed on most Windows 10 and 11 systems. The file is unsigned, so SmartScreen may need **More info**, then **Run anyway**. The x64 installer only runs on Intel or AMD PCs, and the ARM installer only runs on Windows ARM.
~~~~

When you write the real notes file, use a normal fenced `bash` block for the Linux steps, as in `release-notes/RELEASE_NOTES_0.2.1.md`. Do not leave `## Install` as a one-paragraph summary.

**Related docs** (for context when writing highlights; link in release notes only when user-facing):

- [README](../README.md) — overview and the desktop install steps to mirror
- [Developer guide](DEVEL.md) — local setup, smoke tests, full release checklist
- [AGENTS.md](../AGENTS.md) — agent and changelog conventions

**Summary:**  
Write the notes for people downloading a desktop build. Highlights come first and end with a pointer to `dev/CHANGELOG.md` for the detailed changes. `## Install` stays the last section and repeats the six asset names plus how to install on Linux, macOS, and Windows. Update `dev/CHANGELOG.md` for the versioned section and leave an empty `[Unreleased]` section for the next iteration.
