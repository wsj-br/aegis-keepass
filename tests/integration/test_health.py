"""Integration tests for the health endpoint."""

from __future__ import annotations


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data.get("crypto") is True


def test_upload_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"text/html" in resp.content_type.encode() or "html" in resp.data.decode().lower()
