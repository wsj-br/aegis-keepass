"""Unit tests for KeePassEntry helpers, updater, and crypto round-trip."""

from __future__ import annotations

import pytest

from aegis_keepass_lib import (
    AegisEntry,
    AegisParser,
    EntryMatcher,
    KeePassEntry,
    KeePassKdbx,
    KeePassUpdater,
    MatchResult,
)
from app.secure import SecureBytes
from tests.fixtures.builders import (
    AEGIS_PASSWORD,
    AWS_AEGIS_UUID,
    GITHUB_AEGIS_UUID,
    KEEPASS_PASSWORD,
    make_encrypted_aegis_bytes,
    make_kdbx_bytes,
)


class TestKeePassEntryHelpers:
    def test_get_aegis_uuid(self):
        entry = KeePassEntry(
            uuid="x",
            title="T",
            notes=f"some notes\nAegisUUID: {AWS_AEGIS_UUID}\nmore",
        )
        assert entry.get_aegis_uuid() == AWS_AEGIS_UUID

    def test_get_aegis_uuid_missing(self):
        assert KeePassEntry(uuid="x", title="T", notes="plain").get_aegis_uuid() is None
        assert KeePassEntry(uuid="x", title="T").get_aegis_uuid() is None

    def test_has_otp(self):
        assert KeePassEntry(
            uuid="x", title="T", strings={"TimeOtp-Secret-Base32": "ABC"}
        ).has_otp() is True
        assert KeePassEntry(uuid="x", title="T").has_otp() is False

    def test_is_matchable(self):
        assert KeePassEntry(uuid="x", title="T").is_matchable is True
        assert KeePassEntry(uuid="x", title="T", in_recycle_bin=True).is_matchable is False
        assert KeePassEntry(uuid="x", title="T", in_history=True).is_matchable is False

    def test_location_display(self):
        assert KeePassEntry(uuid="x", title="T", group_path="A / B").location_display == "A / B / T"
        assert KeePassEntry(uuid="x", title="T").location_display == "T"

    def test_matchable_entries_filters(self):
        entries = [
            KeePassEntry(uuid="1", title="A"),
            KeePassEntry(uuid="2", title="B", in_recycle_bin=True),
        ]
        assert [e.uuid for e in KeePassKdbx.matchable_entries(entries)] == ["1"]


class TestStripMarkers:
    def test_strip_all_aegis_markers(self):
        notes = f"hello\n\nAegisUUID: {AWS_AEGIS_UUID}\n\nworld"
        cleaned = KeePassUpdater._strip_all_aegis_markers(notes)
        assert "AegisUUID" not in cleaned
        assert "hello" in cleaned
        assert "world" in cleaned

    def test_strip_empty(self):
        assert KeePassUpdater._strip_all_aegis_markers("") == ""
        assert KeePassUpdater._strip_all_aegis_markers(None) == ""  # type: ignore[arg-type]


class TestUpdaterDryRun:
    def test_dry_run_without_py_entry(self):
        aegis = AegisEntry(
            uuid=GITHUB_AEGIS_UUID,
            name="alice",
            issuer="GitHub",
            secret=SecureBytes("JBSWY3DPEHPK3PXP"),
            algo="HMAC-SHA-1",
            digits=6,
            period=30,
        )
        kp = KeePassEntry(uuid="kp", title="GitHub", py_entry=None)
        match = MatchResult(aegis, kp, 0.9, "test")
        updater = KeePassUpdater(kp=None)  # type: ignore[arg-type]
        changes = updater.update_entry(match, dry_run=True)
        assert changes["aegis_uuid"] == GITHUB_AEGIS_UUID
        assert changes["fields_added"] == []
        assert changes["notes_updated"] is False


class TestCryptoRoundTrip:
    def test_open_kdbx_and_uuid_notes(self):
        data = make_kdbx_bytes()
        assert KeePassKdbx.is_kdbx_bytes(data)
        kp = KeePassKdbx.open_bytes(data, KEEPASS_PASSWORD)
        entries, recycle = KeePassKdbx.entries_from_db(kp)
        assert recycle == 0
        by_title = {e.title: e for e in entries}
        assert by_title["Amazon AWS"].get_aegis_uuid() == AWS_AEGIS_UUID

    def test_wrong_keepass_password(self):
        data = make_kdbx_bytes()
        with pytest.raises(ValueError, match="Invalid KeePass"):
            KeePassKdbx.open_bytes(data, "wrong-password")

    def test_apply_match_and_save(self):
        aegis_bytes = make_encrypted_aegis_bytes()
        keepass_bytes = make_kdbx_bytes()
        aegis_entries = AegisParser.parse_bytes(aegis_bytes, AEGIS_PASSWORD)
        kp = KeePassKdbx.open_bytes(keepass_bytes, KEEPASS_PASSWORD)
        keepass_entries, _ = KeePassKdbx.entries_from_db(kp)

        matcher = EntryMatcher()
        matches, _ = matcher.find_matches(aegis_entries, keepass_entries)
        assert matches

        github_match = next(
            m for m in matches if m.aegis_entry.uuid == GITHUB_AEGIS_UUID
        )
        updater = KeePassUpdater(kp)
        changes = updater.apply_match(github_match)
        assert changes["notes_updated"] or "TimeOtp-Secret-Base32" in (
            changes["fields_added"] + changes["fields_updated"]
        )

        saved = updater.save_bytes()
        assert KeePassKdbx.is_kdbx_bytes(saved)

        reopened = KeePassKdbx.open_bytes(saved, KEEPASS_PASSWORD)
        re_entries, _ = KeePassKdbx.entries_from_db(reopened)
        gh = next(e for e in re_entries if e.title == "GitHub")
        assert gh.get_aegis_uuid() == GITHUB_AEGIS_UUID
        assert gh.has_otp()
        assert gh.strings["TimeOtp-Secret-Base32"] == "JBSWY3DPEHPK3PXP"
