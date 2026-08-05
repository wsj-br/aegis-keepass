"""Unit tests for AegisParser and format guards."""

from __future__ import annotations

import json

import pytest

from aegis_keepass_lib import AegisDecryptor, AegisParser, KeePassKdbx
from app.secure import SecureBytes, WipeRegistry
from tests.fixtures.builders import (
    AEGIS_PASSWORD,
    make_encrypted_aegis_bytes,
    make_plaintext_aegis_vault,
)


class TestFormatGuards:
    def test_is_encrypted_vault_true(self):
        assert AegisDecryptor.is_encrypted_vault({"header": {}, "db": "x"}) is True

    def test_is_encrypted_vault_false(self):
        assert AegisDecryptor.is_encrypted_vault({"entries": []}) is False
        assert AegisDecryptor.is_encrypted_vault("nope") is False  # type: ignore[arg-type]

    def test_is_encrypted_bytes_true(self):
        data = make_encrypted_aegis_bytes()
        assert AegisDecryptor.is_encrypted_bytes(data) is True

    def test_is_encrypted_bytes_plaintext_entries(self):
        plaintext = json.dumps(make_plaintext_aegis_vault()).encode()
        assert AegisDecryptor.is_encrypted_bytes(plaintext) is False

    def test_is_encrypted_bytes_garbage(self):
        assert AegisDecryptor.is_encrypted_bytes(b"not-json") is False

    def test_is_kdbx_bytes_false_for_short(self):
        assert KeePassKdbx.is_kdbx_bytes(b"short") is False

    def test_is_kdbx_bytes_false_for_json(self):
        assert KeePassKdbx.is_kdbx_bytes(b'{"header":1,"db":1}') is False


class TestEntriesFromVault:
    def test_algo_map_and_defaults(self):
        vault = {
            "entries": [
                {
                    "uuid": "u1",
                    "name": "n",
                    "issuer": "i",
                    "info": {"secret": "ABC", "algo": "SHA256"},
                },
                {
                    "uuid": "u2",
                    "name": "",
                    "issuer": "",
                    "info": {},
                },
            ]
        }
        entries = AegisParser._entries_from_vault(vault)
        assert len(entries) == 2
        assert entries[0].algo == "HMAC-SHA-256"
        assert entries[0].secret_text() == "ABC"
        assert entries[1].algo == "HMAC-SHA-1"
        assert entries[1].digits == 6
        assert entries[1].period == 30

    def test_unknown_algo_falls_back_to_sha1(self):
        vault = {
            "entries": [
                {
                    "uuid": "u1",
                    "name": "n",
                    "issuer": "i",
                    "info": {"secret": "X", "algo": "MD5"},
                }
            ]
        }
        entries = AegisParser._entries_from_vault(vault)
        assert entries[0].algo == "HMAC-SHA-1"

    def test_registry_tracks_secrets(self):
        registry = WipeRegistry()
        vault = make_plaintext_aegis_vault()
        entries = AegisParser._entries_from_vault(vault, registry=registry)
        assert len(entries) == 3
        registry.wipe_all()
        for entry in entries:
            assert entry.secret_text() == ""


class TestDecryptRoundTrip:
    def test_decrypt_and_parse(self):
        data = make_encrypted_aegis_bytes()
        vault = AegisDecryptor.decrypt_data(data, AEGIS_PASSWORD)
        assert "entries" in vault
        entries = AegisParser.parse_bytes(data, AEGIS_PASSWORD)
        assert len(entries) == 3
        assert entries[0].issuer == "GitHub"
        assert entries[1].algo == "HMAC-SHA-256"

    def test_wrong_password(self):
        data = make_encrypted_aegis_bytes()
        with pytest.raises(RuntimeError, match="Wrong password"):
            AegisDecryptor.decrypt_data(data, SecureBytes("bad-password"))

    def test_parse_rejects_plaintext(self):
        plaintext = json.dumps(make_plaintext_aegis_vault()).encode()
        with pytest.raises(ValueError, match="encrypted"):
            AegisParser.parse_bytes(plaintext, AEGIS_PASSWORD)
