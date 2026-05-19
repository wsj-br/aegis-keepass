# Aegis-KeePass OTP Sync

A Python application to synchronize TOTP (Time-based One-Time Password) secrets from [Aegis Authenticator](https://getaegis.app/) backup files into [KeePass](https://keepass.info/) password manager entries.

## Overview

This tool bridges the gap between Aegis (mobile OTP app) and KeePass (password manager) by:
- **Reading encrypted Aegis backup files** - With secure, in-memory decryption
- Matching entries with KeePass XML entries using fuzzy string matching
- Adding/updating OTP configuration fields (`TimeOtp-Secret-Base32`, etc.)
- Storing Aegis UUID markers in KeePass Notes for future synchronization

## Files

- `aegis_keepass_sync.py` - Command-line sync tool
- `aegis_keepass_web.py` - Interactive web interface for manual matching
- `aegis-backup-*.json` - Input: Encrypted Aegis backup file
- `keepass.xml` - Input/Output: KeePass database in XML format

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

Just copy your Aegis encrypted backup file to the working directory. The tool will decrypt it securely in-memory.

To prompt for the password interactively:

```bash
python3 aegis_keepass_sync.py \
  --aegis aegis-backup-20260414-110439.json \
  --keepass keepass.xml \
  --dry-run
# Enter your Aegis backup password when prompted
```

Or use a password file for automated environments:

```bash
# Create password file (keep secure!)
echo "your-password" > aegis-password.txt
chmod 600 aegis-password.txt

python3 aegis_keepass_sync.py \
  --aegis aegis-backup-20260414-110439.json \
  --keepass keepass.xml \
  --apply \
  --password-file aegis-password.txt
```

## Step 2: Export KeePass to XML

In KeePass:
1. File → Export
2. Select "KeePass XML (2.x)" format
3. Save as `keepass.xml`

## Step 3: Run Sync Tool

### Option A: Command Line (Quick Sync)

**Preview changes with encrypted backup (auto-decrypt):**
```bash
python3 aegis_keepass_sync.py \
  --aegis aegis-backup-20260414-110439.json \
  --keepass keepass.xml \
  --dry-run
```

**Apply changes with encrypted backup:**
```bash
python3 aegis_keepass_sync.py \
  --aegis aegis-backup-20260414-110439.json \
  --keepass keepass.xml \
  --apply
```

**Using a password file (for automation/scripts):**
```bash
python3 aegis_keepass_sync.py \
  --aegis aegis-backup-20260414-110439.json \
  --keepass keepass.xml \
  --apply \
  --password-file aegis-password.txt
```

This will:
- Auto-detect and decrypt the Aegis backup (if encrypted)
- Run the high-precision matching engine to find matching KeePass entries
- Create a new file with `-merged` appended to the name (e.g., `keepass-merged.xml`), leaving the original file completely untouched
- Add/update `TimeOtp-*` fields in matched entries
- Store the `AegisUUID: <uuid>` marker in the Notes field for future syncs
- Automatically generate a timestamped JSON report of matches (e.g. `matching-report-20260519_121418.json`)
- Automatically save the console output to a timestamped log file (e.g. `aegis-keepass-sync-20260519_121418.log`)

### Option B: Web Interface (Interactive Matching)

For entries that don't match automatically or need review:

```bash
# With encrypted backup (will prompt for password)
python3 aegis_keepass_web.py \
  --aegis aegis-backup-20260414-110439.json \
  --keepass keepass.xml \
  --port 5000
```

Then open http://localhost:5000 in your browser to:
- Review automatic matches
- Manually match unmatched entries
- See confidence scores and matching reasons
- Apply changes with visual confirmation

## How Matching Works

The tool uses fuzzy string matching with the following strategy:

1. **Combine Aegis fields**: `issuer + " " + name` (e.g., "GitHub: user-account")
2. **Compare against KeePass Title**: Using difflib.SequenceMatcher
3. **Multiple matching algorithms**:
   - Full identifier vs Title
   - Issuer only vs Title
   - Name only vs Title
   - Substring matching (issuer/name contained in title)



## Linking Alternatives

The tool implements **Option 1** (Notes Marker) by default:

### Option 1: Notes Marker (Implemented)
Stores Aegis UUID in KeePass Notes:
```
Existing notes...

AegisUUID: 5acd3802-1c80-4c10-b1f6-3ca2481a0fbf
```

This enables:
- Future sync to find entries by UUID
- Verification that an entry was synced from Aegis
- No custom fields needed

### Option 2: Custom String Field (Not Implemented)
Could add a custom `Aegis-UUID` field to entries.

### Option 3: Web Application (Implemented)
The `aegis_keepass_web.py` provides an interactive interface for:
- Reviewing matches visually
- Manual matching of ambiguous entries
- Confirming changes before applying

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

1. **Non-destructive Merging**: The merged output is saved as a new file (e.g., `keepass-merged.xml`) instead of overwriting your original database
2. **Dry Run Mode**: Preview all changes before applying
3. **Conflict Detection**: Automatically handles and warns about duplicate matches (e.g., one KeePass entry matched to multiple Aegis entries)
4. **UUID Tracking**: Stores Aegis UUID in the Notes field to guarantee absolute precision on future syncs
5. **Execution Logs**: Automatically saves the full console output to a log file for review

## Sample Output

```
============================================================
AEGIS-KEEPASS SYNC REPORT
============================================================

Total Aegis entries: 40
Matched entries: 39 (97.5%)
Unmatched entries: 1 (2.5%)

--- MATCHED ENTRIES ---
  [UPDATE] Guacamole (pi-server): user
      → Guacamole - pi-server - user
      Confidence: 100.0% (full_id vs title (1.00); issuer vs title (0.89))

  [NEW] GitHub: GitHub:user-account
      → NPM Token - github-user-account
      Confidence: 80.0% (full_id vs title (0.70); name in title)

--- UNMATCHED ENTRIES ---
  [SKIP] Amazon Web Services: Amazon Web Services:root-account-mfa-device@123456789012
```

## Troubleshooting

### Unmatched or Incorrect Matches
The matching engine is now highly optimized to enforce strict service matches, preventing wrong matches. If some entries do not match automatically due to major naming differences, use the interactive web interface to match them manually:
```bash
python3 aegis_keepass_web.py \
  --aegis aegis-backup-20260414-110439.json \
  --keepass keepass.xml
```

### XML Parsing Errors
Ensure KeePass XML export format is "KeePass XML (2.x)"

## Security Notes

- **Backups are decrypted in memory** - no temporary decrypted files are ever created
- If you use `--password-file`, ensure the file has restrictive permissions (`chmod 600`)
- The tool writes to a new merged file (e.g., `keepass-merged.xml`), keeping your original database file completely safe
- Run in dry-run mode first to review changes

## Workflow Summary

```
┌─────────────────┐                                    ┌─────────────────┐
│  Aegis Backup   │───────────────────────────────────▶│                 │
│  (encrypted)    │        Decrypt (in-memory)         │  Python Sync    │
└─────────────────┘                                    │  Tool           │
                                                       │  (this tool)    │
┌─────────────────┐                                    │                 │
│  KeePass XML    │◄───────────────────────────────────│                 │
│  (with OTP)     │                                    └─────────────────┘
└─────────────────┘
```

## License

Licenced under GPLv3. Copyright (c) 2026 Waldemar Scudeller Jr.
