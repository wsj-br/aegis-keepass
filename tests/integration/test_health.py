"""Integration tests for the health endpoint."""

from __future__ import annotations

from app import create_app


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
    assert b"window.AK_DESKTOP = false" in resp.data


def test_desktop_mode_flag_injected(monkeypatch):
    monkeypatch.setenv("AK_DESKTOP", "1")
    monkeypatch.setenv("AK_SYSTEM_THEME", "dark")
    application = create_app()
    client = application.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"window.AK_DESKTOP = true" in resp.data
    assert b'data-desktop="1"' in resp.data
    assert b"window.AK_SYSTEM_THEME = \"dark\"" in resp.data or b"window.AK_SYSTEM_THEME = 'dark'" in resp.data or b'AK_SYSTEM_THEME = "dark"' in resp.data


def test_desktop_system_theme_defaults_dark_when_undetected(monkeypatch):
    monkeypatch.setenv("AK_DESKTOP", "1")
    monkeypatch.delenv("AK_SYSTEM_THEME", raising=False)
    monkeypatch.setattr("app.detect_system_theme", lambda: None)
    application = create_app()
    assert application.config["SYSTEM_THEME"] == "dark"


def test_web_uses_upload_download_terminology(client):
    html = client.get("/").get_data(as_text=True)
    assert "> Upload<" in html or "> Upload</span>" in html
    assert "Upload your files" in html
    assert "Download" in html
    assert "Read your files" not in html


def test_desktop_uses_read_save_terminology(monkeypatch):
    monkeypatch.setenv("AK_DESKTOP", "1")
    application = create_app()
    client = application.test_client()
    html = client.get("/").get_data(as_text=True)
    assert "Read your files" in html
    assert "> Read<" in html or "> Read</span>" in html
    assert "Save" in html
    assert "Upload your files" not in html
    assert "Download merged database" not in html
    js = client.get("/static/js/upload.js").get_data(as_text=True)
    assert "Reading files" in js
    assert "Uploading files to server" in js  # web branch still present
    review_js = client.get("/static/js/review.js").get_data(as_text=True)
    assert "Save merged database" in review_js
    assert "Download merged database" in review_js
