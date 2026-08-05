"""Shared pytest fixtures for unit and Flask integration tests."""

from __future__ import annotations

import io
from typing import Any, Dict, Optional

import pytest

from app import create_app
from tests.fixtures.builders import VaultPair, make_vault_pair


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("SESSION_TIMEOUT_SECONDS", "3600")
    application = create_app()
    application.config["TESTING"] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def session_store(app):
    return app.extensions["session_store"]


@pytest.fixture
def vault_pair() -> VaultPair:
    return make_vault_pair()


@pytest.fixture
def vault_pair_with_keyfile() -> VaultPair:
    return make_vault_pair(with_keyfile=True)


def upload_vault_pair(client, vault: VaultPair, *, wrong_aegis_password: bool = False):
    """POST /api/upload with synthetic vault pair; returns response."""
    data: Dict[str, Any] = {
        "aegis_password": "wrong-password" if wrong_aegis_password else vault.aegis_password,
        "keepass_password": vault.keepass_password,
        "aegis": (io.BytesIO(vault.aegis_bytes), "aegis.json"),
        "keepass": (io.BytesIO(vault.keepass_bytes), "vault.kdbx"),
    }
    if vault.keyfile_bytes is not None:
        data["keyfile"] = (io.BytesIO(vault.keyfile_bytes), "key.key")
    return client.post(
        "/api/upload",
        data=data,
        content_type="multipart/form-data",
    )


def run_upload_process(client, step: str):
    return client.post("/api/upload/process", json={"step": step})


def complete_upload_flow(client, vault: VaultPair) -> Dict[str, Any]:
    """Upload + decrypt_aegis + open_keepass + match. Returns match-step JSON."""
    upload_resp = upload_vault_pair(client, vault)
    assert upload_resp.status_code == 200, upload_resp.get_json()

    for step in ("decrypt_aegis", "open_keepass", "match"):
        resp = run_upload_process(client, step)
        assert resp.status_code == 200, (step, resp.get_json())
        if step == "match":
            return resp.get_json()
    raise AssertionError("match step did not return")


@pytest.fixture
def authed_client(client, vault_pair):
    """Client with an active review session after full upload+match flow."""
    complete_upload_flow(client, vault_pair)
    return client
