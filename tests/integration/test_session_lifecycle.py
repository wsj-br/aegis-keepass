"""Integration tests for save, end-session, and idle timeout."""

from __future__ import annotations

import time

from app import create_app
from tests.conftest import complete_upload_flow
from tests.fixtures.builders import make_vault_pair


def test_end_session_wipes(authed_client, session_store):
    assert len(session_store._sessions) == 1
    resp = authed_client.post("/api/session/end")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["redirect"] == "/"
    assert session_store._sessions == {}

    later = authed_client.get("/api/aegis-entries")
    assert later.status_code == 401


def test_save_returns_kdbx_and_clears_session(authed_client, session_store):
    resp = authed_client.post("/api/save")
    assert resp.status_code == 200
    assert resp.mimetype == "application/octet-stream"
    assert "keepass-merged.kdbx" in resp.headers.get("Content-Disposition", "")
    assert "X-Updated-Count" in resp.headers
    assert "X-Total-Entries" in resp.headers
    data = resp.get_data()
    assert len(data) > 8
    assert data[:4] == b"\x03\xd9\xa2\x9a"

    assert session_store._sessions == {}
    later = authed_client.get("/api/aegis-entries")
    assert later.status_code == 401


def test_save_process_steps_then_download(authed_client, session_store):
    bad = authed_client.post("/api/save/download")
    assert bad.status_code == 400

    cleanup = authed_client.post(
        "/api/save/process",
        json={"step": "cleanup"},
    )
    assert cleanup.status_code == 200
    assert cleanup.get_json()["step"] == "cleanup"
    assert "cleaned_count" in cleanup.get_json()
    assert len(session_store._sessions) == 1

    apply = authed_client.post(
        "/api/save/process",
        json={"step": "apply"},
    )
    assert apply.status_code == 200
    assert "updated_count" in apply.get_json()

    build = authed_client.post(
        "/api/save/process",
        json={"step": "build"},
    )
    assert build.status_code == 200
    body = build.get_json()
    assert body["total"] >= 1
    assert "otp" in body

    unknown = authed_client.post(
        "/api/save/process",
        json={"step": "nope"},
    )
    assert unknown.status_code == 400

    resp = authed_client.post("/api/save/download")
    assert resp.status_code == 200
    assert resp.mimetype == "application/octet-stream"
    assert resp.get_data()[:4] == b"\x03\xd9\xa2\x9a"
    assert session_store._sessions == {}


def test_idle_timeout(monkeypatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("SESSION_TIMEOUT_SECONDS", "1")

    application = create_app()
    application.config["TESTING"] = True
    test_client = application.test_client()
    store = application.extensions["session_store"]

    vault = make_vault_pair()
    complete_upload_flow(test_client, vault)
    assert len(store._sessions) == 1

    # Expire by rewriting last_access (avoid flaky sleep)
    session = next(iter(store._sessions.values()))
    session.last_access = time.time() - 10

    resp = test_client.get("/api/aegis-entries")
    assert resp.status_code == 401
    assert store._sessions == {}
