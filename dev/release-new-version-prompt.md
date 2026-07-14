Create a new release notes file `release-notes/RELEASE_NOTES_<version>.md` for **Aegis-KeePass OTP Sync** using the instructions below. This will be used by `./scripts/release.sh` as part of the GitHub release process (which triggers multi-arch Docker image builds to `ghcr.io/wsj-br/aegis-keepass`).

**Instructions:**

1. **Read `app/_version.py`** to get the current version number (`x.y.z` from `__version__`). If you are preparing notes for a release that is not yet bumped, use the target version you will set there.
2. **Open `dev/CHANGELOG.md`**.
3. **Copy all entries under the `## [Unreleased]` section** up to (but not including) the next `## [` heading (which marks the last released version).
4. **Format the new file** according to the prior release notes in `release-notes/RELEASE_NOTES_x.y.z.md`:
   - Title: `# Release <version>` (e.g. `# Release 0.2.0`)
   - Opening line: one sentence describing what this release is (for the first release, “First public release…”; for later releases, a short summary of the theme).
   - `## Highlights` — Summarize the most important user-facing changes from the changelog bullets (focus on features, fixes, and major improvements; don't list every change verbatim—write clear, user-focused summaries).
   - `## Docker` — Include pull and run commands using the version tag (not only `latest`):

     ```bash
     docker pull ghcr.io/wsj-br/aegis-keepass:<version>
     docker run --rm -p 127.0.0.1:8580:8580 ghcr.io/wsj-br/aegis-keepass:<version>
     ```

     Follow with: `Open [http://localhost:8580](http://localhost:8580).`

     Optionally note that start scripts are attached to the GitHub Release as downloadable assets.
   - Optionally add `## Changes` with the detailed changelog bullets (Added / Changed / Fixed / etc.) if the highlights alone would omit useful detail for operators or developers.
   - Don't include the `## [Unreleased]` heading from the changelog.
5. **Update `dev/CHANGELOG.md`**:
   - Move all lines from `[Unreleased]` to a new section with the current version and today's date (`## [x.y.z] - YYYY-MM-DD`).
   - Leave an empty `[Unreleased]` section at the top for future work.

**Prerequisites (confirm before finishing):**

- `app/_version.py` has `__version__ = "<version>"` matching the notes filename.
- `release-notes/RELEASE_NOTES_<version>.md` exists and matches the style of prior notes.
- Changes are committed on a clean tree before running `./scripts/release.sh` (use `--dry-run` first).

**Example format for the file:**

```markdown
# Release 0.2.0

Developer documentation and agent workflow improvements.

## Highlights

- Briefly state the most important new features, fixes, or improvements.
- Focus on what most directly affects users running the Docker image or web UI.

## Docker

```bash
docker pull ghcr.io/wsj-br/aegis-keepass:0.2.0
docker run --rm -p 127.0.0.1:8580:8580 ghcr.io/wsj-br/aegis-keepass:0.2.0
```

Open [http://localhost:8580](http://localhost:8580).
```

**Related docs** (for context when writing highlights; link in release notes only when user-facing):

- [README](../README.md) — overview, quick start, security model
- [Developer guide](DEVEL.md) — local setup, smoke tests, full release checklist
- [AGENT.md](../AGENT.md) — agent and changelog conventions

**Summary:**  
Ensure the new release notes file follows the format of `release-notes/RELEASE_NOTES_0.1.0.md`, highlights user-facing changes from the changelog, updates `dev/CHANGELOG.md` for the versioned section, and leaves the changelog ready for the next iteration. Write clearly and concisely for GitHub users pulling the published Docker image.
