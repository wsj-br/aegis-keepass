# Product

## Platform

desktop

## Users

People who already use Aegis Authenticator and KeePass, KeePassXC, or a compatible client, and want their OTP secrets available inside their password vault. Typical situation: a personal, localhost session where they bring their own encrypted backups and leave with a merged database.

## Product Purpose

Import and sync TOTP secrets from an encrypted Aegis backup into a KeePass `.kdbx` database. The implemented flow is read → review matches → save a merged database (the loopback web fallback labels the same steps upload → review → download). Success means the user can confirm matches (and fix misses), receive native KeePass `TimeOtp-*` fields on the right entries, and leave the session with sensitive data wiped on save or session end.

## Positioning

Both inputs stay encrypted until processed in memory: encrypted Aegis JSON and encrypted `.kdbx`. Secrets and uploaded files are not retained after use; session material is securely wiped when the user saves or ends the session. The app runs as a desktop window on the user's computer and serves its UI on loopback only. The tool works from an encrypted Aegis backup into KeePass TOTP fields without requiring a plaintext Aegis export.

## Operating Context

Single-user, trusted use on the person's own computer. Users supply an encrypted Aegis `.json` backup, a KeePass `.kdbx`, passwords, and an optional keyfile. Matching is reviewed in the app window before apply. Compatible clients include KeePass 2.x, KeePassXC, and Keepass2Android for the written TOTP fields. The desktop process binds its HTTP server to loopback.

## Capabilities and Constraints

- Upload encrypted Aegis backup and KeePass database; decrypt and process in server memory for the session.
- Fuzzy match Aegis entries to KeePass titles; prefer existing `AegisUUID` markers in Notes on re-import; support manual linking and conflict surfacing.
- Apply native KeePass TOTP fields (`TimeOtp-Secret-Base32`, period, digits, algorithm) and record `AegisUUID` in Notes for future re-imports.
- Stream a merged encrypted `.kdbx` through the native Save dialog; wipe session state afterward.
- Intended for single-user operation on the local machine; no login layer.
- The UI must work without internet: CSS, JS, icons, and fonts ship inside the desktop app (`app/static/`, system UI fonts only). No CDN or remote asset loads.
- Plain (unencrypted) Aegis JSON backups are not supported.
- Memory wiping is best-effort within ordinary process memory limits; not an HSM or formal secret-management product.

## Brand Commitments

Product name: **Aegis-KeePass OTP Sync**. Public repo: `wsj-br/aegis-keepass`. Licensed under GPL-3.0. Copyright (c) 2026 Waldemar Scudeller Jr. Brand mark: approved vault-shield **AK** logo (option A) shipped as local static assets under `app/static/img/` (`logo.png`, favicons). No separate brand voice guide was confirmed.

## Evidence on Hand

- User-facing product description and security model in `README.md`.
- Runnable UI: `app/templates/` (upload, review), `app/static/css/app.css`, `app/static/js/`, brand mark under `app/static/img/`.
- Approved logo ships at `app/static/img/logo.png` (option A).
- No customer testimonials, case studies, benchmarks, or pricing claims exist; future work must not fabricate them.

## Product Principles

1. Treat encrypted backups and credentials as transient session material — process, then wipe; do not retain.
2. Prefer clarity and control over automation theater: matching helps, review decides.
3. Stay honest about the security model and its limits; never overclaim permanence of wipe or multi-tenant safety.
4. Preserve the single-user, on-this-computer operating assumption in product defaults.
5. Keep the product job narrow: get Aegis OTP into KeePass with native fields and reliable re-import markers.
6. Keep the UI offline-capable: every script and style the pages need is local in the app.
