"""Guard: UI must work offline — no remote scripts, stylesheets, or fonts."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"

# Resource tags that would pull bytes from the network if given an absolute URL.
_REMOTE_RESOURCE = re.compile(
    r"""(?ix)
    <(?:script|link|img|source|iframe|audio|video|object|embed)\b[^>]*?\b
    (?:src|href)\s*=\s*["'](https?:)?//
    """
)

# CSS/JS fetches that leave the origin.
_REMOTE_CSS_JS = re.compile(
    r"""(?ix)
    (?:@import\s+|url\(\s*)["']?https?://
    |(?:src|href)\s*=\s*["']https?://
    """
)

# SVG xmlns and similar XML namespaces are not network fetches.
_ALLOW_IN_TEMPLATES = (
    "http://www.w3.org/",
)


def _iter_ui_files():
    for path in (APP / "templates").rglob("*"):
        if path.is_file() and path.suffix in {".html", ".jinja", ".j2"}:
            yield path
    for path in (APP / "static").rglob("*"):
        if path.is_file() and path.suffix in {".css", ".js", ".html"}:
            yield path


def test_static_bundle_is_present_for_docker():
    required = [
        APP / "static" / "css" / "app.css",
        APP / "static" / "js" / "theme.js",
        APP / "static" / "js" / "upload.js",
        APP / "static" / "js" / "review.js",
        APP / "static" / "img" / "logo.png",
        APP / "static" / "img" / "favicon.png",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    assert not missing, f"Missing local UI assets that Docker must ship: {missing}"


def test_templates_and_static_have_no_remote_assets():
    offenders = []
    for path in _iter_ui_files():
        text = path.read_text(encoding="utf-8")
        for match in _REMOTE_RESOURCE.finditer(text):
            snippet = text[match.start() : match.start() + 120].replace("\n", " ")
            if any(allow in snippet for allow in _ALLOW_IN_TEMPLATES):
                continue
            offenders.append(f"{path.relative_to(ROOT)}: {snippet}")
        for match in _REMOTE_CSS_JS.finditer(text):
            snippet = text[match.start() : match.start() + 120].replace("\n", " ")
            if any(allow in snippet for allow in _ALLOW_IN_TEMPLATES):
                continue
            # Footer GitHub navigation link is optional; it is not loaded as an asset.
            if 'github_repo_url' in snippet or 'github.com/wsj-br/aegis-keepass' in snippet:
                continue
            if path.name == "base.html" and "github" in snippet.lower():
                continue
            offenders.append(f"{path.relative_to(ROOT)}: {snippet}")
    assert not offenders, "Remote UI asset references found:\n" + "\n".join(offenders)


@pytest.mark.parametrize("path", ["/",])
def test_upload_page_serves_local_static_urls(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'href="/static/css/app.css"' in html or "static/css/app.css" in html
    assert "static/js/theme.js" in html
    assert "static/js/toast.js" in html
    assert "https://fonts." not in html
    assert "cdn." not in html.lower()
    assert "jsdelivr" not in html.lower()
    assert "unpkg.com" not in html.lower()


def test_static_files_are_served_locally(client):
    for url in (
        "/static/css/app.css",
        "/static/js/theme.js",
        "/static/js/toast.js",
        "/static/js/upload.js",
        "/static/js/review.js",
        "/static/img/logo.png",
        "/static/img/favicon.png",
    ):
        resp = client.get(url)
        assert resp.status_code == 200, url
        assert len(resp.data) > 0


def test_upload_page_includes_local_logo(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "static/img/logo.png" in html
    assert "static/img/favicon.png" in html
