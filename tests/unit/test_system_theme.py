"""Unit tests for desktop OS theme detection."""

from __future__ import annotations

from app.system_theme import (
    detect_system_theme,
    prepare_desktop_system_theme,
    system_theme_from_environ,
)


def test_system_theme_from_environ(monkeypatch):
    monkeypatch.delenv('AK_SYSTEM_THEME', raising=False)
    assert system_theme_from_environ() is None
    monkeypatch.setenv('AK_SYSTEM_THEME', 'dark')
    assert system_theme_from_environ() == 'dark'
    monkeypatch.setenv('AK_SYSTEM_THEME', 'LIGHT')
    assert system_theme_from_environ() == 'light'
    monkeypatch.setenv('AK_SYSTEM_THEME', 'nope')
    assert system_theme_from_environ() is None


def test_detect_prefers_windows_registry_on_wsl(monkeypatch):
    monkeypatch.setenv('WSL_DISTRO_NAME', 'Ubuntu')
    monkeypatch.setattr('app.system_theme._windows_apps_use_light_theme', lambda: False)
    monkeypatch.setattr('app.system_theme._linux_color_scheme', lambda: 'light')
    monkeypatch.setattr('sys.platform', 'linux')
    assert detect_system_theme() == 'dark'


def test_detect_linux_gsettings_when_not_wsl(monkeypatch):
    monkeypatch.delenv('WSL_DISTRO_NAME', raising=False)
    monkeypatch.delenv('WSL_INTEROP', raising=False)
    monkeypatch.setattr('app.system_theme._is_wsl', lambda: False)
    monkeypatch.setattr('app.system_theme._linux_color_scheme', lambda: 'dark')
    monkeypatch.setattr('sys.platform', 'linux')
    assert detect_system_theme() == 'dark'


def test_prepare_desktop_falls_back_to_dark(monkeypatch):
    monkeypatch.setattr('app.system_theme.detect_system_theme', lambda: None)
    monkeypatch.setattr('app.system_theme.apply_gtk_prefer_dark', lambda _dark: None)
    assert prepare_desktop_system_theme() == 'dark'
    assert system_theme_from_environ() == 'dark'
