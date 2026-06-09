# Aegis-KeePass OTP Sync

Import TOTP (Time-based One-Time Password) secrets from [Aegis Authenticator](https://getaegis.app/) backup files into [KeePass](https://keepass.info/) password manager entries. Review matches in the browser, then save a merged KeePass XML file.

## Overview

This tool bridges the gap between Aegis (mobile OTP app) and KeePass (password manager) by:
- **Importing** OTP secrets from encrypted Aegis backups (decrypted securely in memory)
- **Matching** Aegis entries to KeePass XML entries using fuzzy string matching
- **Applying** OTP configuration fields (`TimeOtp-Secret-Base32`, etc.) to matched entries
- **Merging** the result into a new KeePass XML file, leaving your original export untouched
- Storing Aegis UUID markers in KeePass Notes for future re-imports

The web interface lets you review automatic matches, fix ambiguous ones manually, and save the merged KeePass XML when you are ready.

## Files

- `aegis_keepass_web.py` — Interactive web interface (main entry point)
- `aegis_keepass_lib.py` — Shared parsing, matching, and KeePass update logic
- `aegis-backup-*.json` — Input: encrypted Aegis backup file
- `keepass.xml` — Input/Output: KeePass database in XML format

## Prerequisites

- Python 3.9+ (with `python3-venv` package: `sudo apt install python3-venv`)
- KeePass database exported to XML format
- Encrypted Aegis backup file
- `cryptography` library (required): `pip install cryptography`

## Installation

Create and activate a virtual environment (recommended for isolated dependencies):

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install all requirements (includes cryptography for encrypted backups)
pip install -r requirements.txt
```

**Note:** On systems with externally managed Python (PEP 668), use a virtual environment or install via apt: `sudo apt install python3-venv python3-cryptography`

## Step 1: Prepare Aegis Backup

Copy your Aegis encrypted backup file to the working directory. The tool decrypts it securely in memory — no temporary decrypted files are created.

Optionally create a password file for automation:

```bash
echo "your-password" > aegis-password.txt
chmod 600 aegis-password.txt
```

## Step 2: Export KeePass to XML

In KeePass:
1. File → Export
2. Select "KeePass XML (2.x)" format
3. Save as `keepass.xml`

## Step 3: Run the Web Interface

```bash
# Fully interactive — prompts for any missing arguments
python3 aegis_keepass_web.py

# Partial — only prompts for what you omit
python3 aegis_keepass_web.py --aegis aegis-backup-YYYYMMDD-HHMMSS.json

# Explicit paths (password prompted interactively if omitted)
python3 aegis_keepass_web.py \
  --aegis aegis-backup-YYYYMMDD-HHMMSS.json \
  --keepass keepass.xml \
  --port 5000

# Non-interactive password via file
python3 aegis_keepass_web.py \
  --aegis aegis-backup-YYYYMMDD-HHMMSS.json \
  --keepass keepass.xml \
  --password-file aegis-password.txt
```

When run without all arguments, the CLI guides you through setup:

- **Aegis backup** (`--aegis`): lists `.json` files in the current folder; use ↑/↓ to select, Enter to confirm
- **KeePass XML** (`--keepass`): lists `.xml` files the same way
- **Aegis password** (if `--password-file` is not set): choose **Enter password** or **Read password from file**; if you pick a file, `.txt` files in the current folder are listed for selection

Each file picker also includes `[Enter path manually]` as the last option if the file is elsewhere. Use **Esc** to cancel. In non-interactive terminals (pipes, CI), plain text prompts are used instead.

Then open http://localhost:5000 in your browser to:
- **Match** — review automatic matches and manually link unmatched entries
- **Apply** — confirm which OTP secrets to copy into each KeePass entry
- **Merge** — click **Save Merged File** to apply OTP secrets and write the merged KeePass XML
- **Close** — click **Close** in the header when you are done (or close the browser tab)

The merged output file uses `-merged` in the name (e.g. `keepass-merged.xml`); your original export is never overwritten.

### Console output

The terminal stays quiet while you use the web UI — routine API requests are not logged. You still see startup messages and match counts. When you save a merged file, the console prints the file name and full path:

```
Merged file saved:
  Name: keepass-merged.xml
  Path: /home/you/project/keepass-merged.xml
```

### Stopping the server

The local web server stops automatically when you:
- Click **Close** in the app header (after confirming)
- Close the browser tab (refreshing the page does **not** stop the server)

You can also press **Ctrl+C** in the terminal at any time.

## How Matching Works

The tool uses fuzzy string matching with the following strategy:

1. **Combine Aegis fields**: `issuer + " " + name` (e.g., "GitHub: user-account")
2. **Compare against KeePass Title**: Using difflib.SequenceMatcher
3. **Multiple matching algorithms**:
   - Full identifier vs Title
   - Issuer only vs Title
   - Name only vs Title
   - Substring matching (issuer/name contained in title)

## Linking Strategy

Aegis UUIDs are stored in KeePass Notes:

```
Existing notes...

AegisUUID: 00000000-0000-4000-8000-000000000001
```

This enables:
- Future re-imports to find entries by UUID
- Verification that an entry was imported from Aegis
- No custom fields needed

## OTP Fields Added to KeePass

For each matched entry, these fields are added/updated:

| Field | Description | Example |
|-------|-------------|---------|
| `TimeOtp-Secret-Base32` | TOTP secret (Base32 encoded) | `ORSXG5BRGIZTINJW` |
| `TimeOtp-Period` | Time period in seconds | `30` |
| `TimeOtp-Digits` | Number of OTP digits | `6` |
| `TimeOtp-Algorithm` | Hash algorithm | `SHA1` |

These fields are compatible with KeePass plugins like:
- KeePassOTP
- KeeTrayTOTP

## Safety Features

1. **Non-destructive merge**: output is saved as a new file (e.g. `keepass-merged.xml`) instead of overwriting your original database
2. **Visual review**: review and adjust every match before applying OTP secrets
3. **Conflict detection**: warns when a KeePass entry is already linked to another Aegis entry
4. **UUID tracking**: stores Aegis UUID in the Notes field for precise future re-imports
5. **Secure deletion**: after usage, use `clean_data.sh` to securely delete sensitive files in the working directory

## Troubleshooting

### Unmatched or Incorrect Matches

If some entries do not match automatically due to naming differences, use the web UI to match them manually — click **Select** or **Suggest** on the unmatched row.

### XML Parsing Errors

Ensure KeePass XML export format is "KeePass XML (2.x)"

## Security Notes

- Ensure the Aegis backup file and the original KeePass XML files have restrictive permissions (`chmod 600`)
- **Backups are decrypted in memory** — no temporary decrypted files are ever created
- If you use `--password-file`, ensure that file also has restrictive permissions (`chmod 600`)
- The tool writes the output to a new merged file (e.g. `keepass-merged.xml`) with restrictive permissions, keeping your original database file completely safe
- Review matches in the browser before clicking **Save Merged File** to apply and merge; use **Close** or close the tab when finished so the local server does not keep running

## Workflow Summary

```
┌─────────────────┐     decrypt      ┌──────────────────────┐     merge     ┌────────────────────────┐
│  Aegis Backup   │─────────────────>|  aegis_keepass_web   │──────────────>|  Merged KeePass XML    │
│  (encrypted)    │   import OTP     │  match · apply       │               │       (with OTP)       │
└─────────────────┘                  └──────────┬───────────┘               └────────────────────────┘
                                                ^
┌─────────────────┐                             │
│  KeePass XML    │─────────────────────────────┘
│  (original)     │
└─────────────────┘
```

## License

Licenced under GPLv3. Copyright (c) 2026 Waldemar Scudeller Jr.
