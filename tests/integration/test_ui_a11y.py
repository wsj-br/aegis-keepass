"""Guard accessibility wiring on upload and review pages."""

from __future__ import annotations

import re


def _file_input_tag(html: str, input_id: str) -> str:
    match = re.search(rf'<input[^>]*\bid="{re.escape(input_id)}"[^>]*>', html)
    assert match, f"missing input#{input_id}"
    return match.group(0)


def test_upload_file_inputs_are_keyboard_reachable(client):
    html = client.get("/").get_data(as_text=True)
    for input_id in ("aegis-input", "keepass-input"):
        tag = _file_input_tag(html, input_id)
        assert "visually-hidden" in tag
        # Bare HTML hidden attribute removes the control from the tab order.
        assert not re.search(r"(?<![\w-])hidden(?![\w-])", tag), tag
    assert "visually-hidden" in client.get("/static/css/app.css").get_data(as_text=True)


def test_upload_password_fields_have_visibility_toggle(client):
    html = client.get("/").get_data(as_text=True)
    assert html.count('data-password-toggle=') == 2
    assert 'aria-label="Show password"' in html
    assert "password-field" in html
    js = client.get("/static/js/upload.js").get_data(as_text=True)
    assert "data-password-toggle" in js
    css = client.get("/static/css/app.css").get_data(as_text=True)
    assert ".password-toggle" in css


def test_css_adapts_touch_and_safe_areas(client):
    css = client.get("/static/css/app.css").get_data(as_text=True)
    assert "@media (pointer: coarse)" in css
    assert "min-height: 44px" in css
    assert "safe-area-inset" in css
    html = client.get("/").get_data(as_text=True)
    assert "viewport-fit=cover" in html


def test_css_reduced_motion_is_targeted(client):
    css = client.get("/static/css/app.css").get_data(as_text=True)
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "animation-duration: 0.01ms" not in css
    assert "--motion-fast" in css
    assert "progress-spin" in css
    # Static alternate for the looping progress cue
    assert "animation: none" in css


def test_review_page_has_dialog_and_filter_semantics(authed_client):
    html = authed_client.get("/review").get_data(as_text=True)
    assert html.count('role="dialog"') >= 5
    assert 'aria-labelledby="conflict-title"' in html
    assert 'aria-labelledby="picker-title"' in html
    assert 'aria-labelledby="save-modal-title"' in html
    assert 'aria-labelledby="end-session-title"' in html
    assert 'id="save-progress-steps"' in html
    assert html.count('aria-hidden="true"') >= 5
    assert 'aria-pressed="true"' in html
    assert 'data-status="no_uuid"' in html
    assert 'id="complete-restart-btn"' in html
    assert 'Start new merge' in html
    assert 'for="aegis-filter"' in html
    assert 'for="keepass-search"' in html
    assert 'id="picker-cancel-btn"' in html
    assert "<caption" in html
    assert 'scope="col"' in html
    js = authed_client.get("/static/js/review.js").get_data(as_text=True)
    assert "dialogStack" in js
    assert "Escape" in js
    assert "syncFilterPressed" in js
    assert "SAVE_STEPS" in js
    assert "window.confirm" not in js
    assert "confirm(" not in js
    assert 'setAttribute(\'aria-hidden\'' in js or 'setAttribute("aria-hidden"' in js
    toast = authed_client.get("/static/js/toast.js").get_data(as_text=True)
    assert "showToast" in toast
    assert "hideTimer" in toast


def test_css_invalid_and_sticky_review_table(client):
    css = client.get("/static/css/app.css").get_data(as_text=True)
    assert 'aria-invalid="true"' in css
    assert "position: sticky" in css
    assert "max-height: min(70vh, 720px)" in css
