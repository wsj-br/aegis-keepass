"""Integration tests for upload validation and process flow."""

from __future__ import annotations

import io
import json
from dataclasses import replace

from tests.conftest import complete_upload_flow, run_upload_process, upload_vault_pair
from tests.fixtures.builders import (
    AEGIS_PASSWORD,
    KEEPASS_PASSWORD,
    make_encrypted_aegis_bytes,
    make_plaintext_aegis_vault,
    make_vault_pair,
)


def test_upload_missing_files(client, session_store):
    resp = client.post(
        "/api/upload",
        data={"aegis_password": "x", "keepass_password": "y"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert session_store._sessions == {}


def test_upload_rejects_plaintext_aegis(client, session_store, vault_pair):
    plaintext = json.dumps(make_plaintext_aegis_vault()).encode()
    resp = client.post(
        "/api/upload",
        data={
            "aegis_password": AEGIS_PASSWORD,
            "keepass_password": KEEPASS_PASSWORD,
            "aegis": (io.BytesIO(plaintext), "aegis.json"),
            "keepass": (io.BytesIO(vault_pair.keepass_bytes), "vault.kdbx"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "encrypted" in resp.get_json()["error"].lower()
    assert session_store._sessions == {}


def test_upload_rejects_non_kdbx(client, session_store, vault_pair):
    resp = client.post(
        "/api/upload",
        data={
            "aegis_password": AEGIS_PASSWORD,
            "keepass_password": KEEPASS_PASSWORD,
            "aegis": (io.BytesIO(vault_pair.aegis_bytes), "aegis.json"),
            "keepass": (io.BytesIO(b"not-a-kdbx-file"), "vault.kdbx"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "kdbx" in resp.get_json()["error"].lower()
    assert session_store._sessions == {}


def test_happy_path_upload_to_review(client, vault_pair, session_store):
    match_json = complete_upload_flow(client, vault_pair)
    assert match_json["success"] is True
    assert match_json["redirect"] == "/review"
    assert match_json["stats"]["aegis_total"] == 3
    assert match_json["stats"]["matched"] >= 1
    assert match_json["stats"]["unmatched"] >= 1

    review = client.get("/review")
    assert review.status_code == 200

    entries = client.get("/api/aegis-entries")
    assert entries.status_code == 200
    body = entries.get_json()
    assert body["stats"]["total"] == 3
    assert body["stats"]["matched"] == match_json["stats"]["matched"]


def test_wrong_aegis_password_destroys_session(client, vault_pair, session_store):
    # Upload with correct password so session is created, then we need wrong
    # password at decrypt — passwords are stored at upload time, so craft a
    # vault encrypted with a different password than we submit.
    wrong_pair = make_vault_pair()
    # Encrypt Aegis with a different password but upload claiming AEGIS_PASSWORD
    aegis = make_encrypted_aegis_bytes(password="other-aegis-pass")
    vault = replace(wrong_pair, aegis_bytes=aegis, aegis_password=AEGIS_PASSWORD)

    upload_resp = upload_vault_pair(client, vault)
    assert upload_resp.status_code == 200
    assert len(session_store._sessions) == 1

    resp = run_upload_process(client, "decrypt_aegis")
    assert resp.status_code == 400
    assert session_store._sessions == {}

    later = client.get("/api/aegis-entries")
    assert later.status_code == 401


def test_auth_gates_without_cookie(client):
    assert client.get("/api/aegis-entries").status_code == 401
    review = client.get("/review")
    assert review.status_code in (302, 301)
    assert review.headers["Location"].endswith("/")
