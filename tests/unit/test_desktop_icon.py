"""The desktop window icon is the app logo."""

from __future__ import annotations

import sys

from app.desktop_icon import logo_png_path, png_to_icns, png_to_ico, window_icon_path


def test_logo_png_is_the_window_icon_on_posix():
    path = window_icon_path()
    assert path == str(logo_png_path())
    assert logo_png_path().is_file()


def test_png_wrappers_keep_the_logo_bytes():
    png = logo_png_path().read_bytes()
    ico = png_to_ico(png)
    icns = png_to_icns(png)
    assert ico[:4] == b"\x00\x00\x01\x00"
    assert png in ico
    assert icns[:4] == b"icns"
    assert png in icns


def test_windows_icon_is_an_ico(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    path = window_icon_path()
    assert path is not None
    assert path.endswith("aegis-keepass-logo.ico")
    assert (tmp_path / "aegis-keepass-logo.ico").read_bytes().startswith(b"\x00\x00\x01\x00")


def test_linux_desktop_entry_points_at_the_logo(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")
    from app.desktop_icon import APP_ID, install_linux_desktop_entry

    desktop = install_linux_desktop_entry()
    assert desktop == tmp_path / "applications" / f"{APP_ID}.desktop"
    text = desktop.read_text(encoding="utf-8")
    icon = tmp_path / "aegis-keepass" / "logo.png"
    assert icon.is_file()
    assert f"Icon={icon}\n" in text
    assert f"StartupWMClass={APP_ID}\n" in text
    assert "Name=Aegis-KeePass OTP Sync\n" in text


def test_linux_desktop_entry_uses_the_appimage_path(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("APPIMAGE", "/home/user/aegis-keepass.AppImage")
    monkeypatch.setattr(sys, "platform", "linux")
    from app.desktop_icon import install_linux_desktop_entry

    desktop = install_linux_desktop_entry()
    text = desktop.read_text(encoding="utf-8")
    assert "Exec=/home/user/aegis-keepass.AppImage\n" in text
