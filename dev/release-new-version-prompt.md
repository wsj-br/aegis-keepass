Create a new release notes file `release-notes/RELEASE_NOTES_<version>.md` for **Aegis-KeePass OTP Sync** using the instructions below. This will be used by `./scripts/release.sh` as part of the GitHub release process (which triggers desktop builds for Linux AMD64, Linux ARM64, macOS Intel, macOS Apple Silicon, Windows x64, and Windows ARM).

**Instructions:**

1. **Read `app/_version.py`** (or run `./scripts/version`) to get the current version number (`x.y.z` from `__version__`). If you are preparing notes for a release that is not yet bumped, use the target version you will set with `./scripts/version X.Y.Z`.
2. **Open `dev/CHANGELOG.md`**.
3. **Copy all entries under the `## [Unreleased]` section** up to (but not including) the next `## [` heading (which marks the last released version).
4. **Format the new file** like the example below (highlights, then a desktop install section that names the six release assets):
   - Title: `# Release <version>` (e.g. `# Release 0.2.0`)
   - Opening line: one sentence describing what this release is (for the first release, “First public release…”; for later releases, a short summary of the theme).
   - `## Highlights` — Summarize the most important user-facing changes from the changelog bullets (focus on features, fixes, and major improvements; don't list every change verbatim—write clear, user-focused summaries).
   - `## Install` — Tell people to download the asset for their computer from the GitHub Release. Name all six files for this version:

     - Linux AMD64: `aegis-keepass-<version>-linux-amd64.tar.gz`
     - Linux ARM64: `aegis-keepass-<version>-linux-arm64.tar.gz`
     - macOS Intel: `aegis-keepass-<version>-macos-intel.dmg` (open the disk image and drag the app to Applications)
     - macOS Apple Silicon: `aegis-keepass-<version>-macos-arm64.dmg`
     - Windows x64: `aegis-keepass-<version>-windows-x64.zip`
     - Windows ARM: `aegis-keepass-<version>-windows-arm64.zip`

     Mention the Linux GTK/WebKit packages, Windows WebView2, and that the macOS build is unsigned (right-click **Open**, then **Open Anyway** if Gatekeeper blocks it). Link the release page.
   - Optionally add `## Changes` with the detailed changelog bullets (Added / Changed / Fixed / etc.) if the highlights alone would omit useful detail.
   - Don't include the `## [Unreleased]` heading from the changelog.
5. **Update `dev/CHANGELOG.md`**:
   - Move all lines from `[Unreleased]` to a new section with the current version and today's date (`## [x.y.z] - YYYY-MM-DD`).
   - Leave an empty `[Unreleased]` section at the top for future work.

**Prerequisites (confirm before finishing):**

- `app/_version.py` has `__version__ = "<version>"` matching the notes filename (`./scripts/version` prints that version).
- `release-notes/RELEASE_NOTES_<version>.md` exists and matches the style of prior notes, with an `## Install` section for the desktop assets.
- Changes are committed on a clean tree before running `./scripts/release.sh` (use `--dry-run` first).

**Example format for the file:**

```markdown
# Release 0.2.0

Short summary of what this release is.

## Highlights

- Briefly state the most important new features, fixes, or improvements.
- Focus on what people using the desktop app will notice.

## Install

Download the build for your computer from the [GitHub Release](https://github.com/wsj-br/aegis-keepass/releases/tag/v0.2.0):

- Linux AMD64: `aegis-keepass-0.2.0-linux-amd64.tar.gz`
- Linux ARM64: `aegis-keepass-0.2.0-linux-arm64.tar.gz`
- macOS Intel: `aegis-keepass-0.2.0-macos-intel.dmg`
- macOS Apple Silicon: `aegis-keepass-0.2.0-macos-arm64.dmg`
- Windows x64: `aegis-keepass-0.2.0-windows-x64.zip`
- Windows ARM: `aegis-keepass-0.2.0-windows-arm64.zip`

On macOS, open the DMG and drag **Aegis-KeePass OTP Sync** to Applications. The build is unsigned: right-click **Open** the first time. On Linux, install GTK 3 and WebKitGTK before launching. On Windows, Edge WebView2 Runtime is required (usually already installed).
```

**Related docs** (for context when writing highlights; link in release notes only when user-facing):

- [README](../README.md) — overview, install, security model
- [Developer guide](DEVEL.md) — local setup, smoke tests, full release checklist
- [AGENTS.md](../AGENTS.md) — agent and changelog conventions

**Summary:**  
Ensure the new release notes file follows the format above, highlights user-facing changes from the changelog, updates `dev/CHANGELOG.md` for the versioned section, and leaves the changelog ready for the next iteration. Write clearly for people downloading a desktop build from the GitHub Release.
