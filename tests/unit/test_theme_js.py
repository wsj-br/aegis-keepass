"""Guards for desktop theme-toggle behavior when localStorage is missing."""

from __future__ import annotations

from pathlib import Path

THEME_JS = Path(__file__).resolve().parents[2] / 'app' / 'static' / 'js' / 'theme.js'


def test_theme_js_does_not_rely_solely_on_local_storage():
    source = THEME_JS.read_text(encoding='utf-8')
    assert "typeof localStorage === 'undefined'" in source
    assert "data-theme-pref" in source
    assert 'memoryPref' in source
    assert 'set_prefer_dark' in source
