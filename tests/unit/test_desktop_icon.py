"""The desktop window icon is the app logo."""

from __future__ import annotations

import sys
import shutil
import subprocess

import pytest

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
    assert 'Exec="/home/user/aegis-keepass.AppImage"\n' in text


def test_linux_desktop_entry_preserves_manager_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    monkeypatch.setattr(sys, 'platform', 'linux')
    from app.desktop_icon import APP_ID, install_linux_desktop_entry

    desktop = tmp_path / 'applications' / f'{APP_ID}.desktop'
    desktop.parent.mkdir()
    managed = '[Desktop Entry]\nName=Managed\nExec=/managed/app\nActions=Uninstall;\n'
    desktop.write_text(managed)
    assert install_linux_desktop_entry() == desktop
    assert desktop.read_text() == managed


@pytest.mark.parametrize('name', [
    'Aegis-KeePass OTP Sync',
    "Aegis-KeePass user's Sync",
])
def test_desktop_exec_round_trips_with_gio(monkeypatch, tmp_path, name):
    # Use the actual desktop-entry parser, not shlex (which accepts the bug).
    system_python = '/usr/bin/python3'
    if not sys.platform.startswith('linux') or not shutil.which(system_python):
        pytest.skip('Desktop parser validation requires Linux system Python')
    check = subprocess.run([system_python, '-c', 'from gi.repository import Gio'],
                           capture_output=True)
    if check.returncode:
        pytest.skip('System PyGObject is required for desktop parser validation')
    from app.desktop_icon import install_linux_desktop_entry

    executable = tmp_path / name
    executable.write_text('#!/bin/sh\ntouch "$(dirname "$0")/launched"\n')
    executable.chmod(0o755)
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    monkeypatch.setenv('APPIMAGE', str(executable))
    monkeypatch.setattr(sys, 'platform', 'linux')
    desktop = install_linux_desktop_entry()
    if shutil.which('desktop-file-validate'):
        subprocess.run(['desktop-file-validate', str(desktop)], check=True)
    subprocess.run([system_python, '-c', '''
import sys
import time
from pathlib import Path
from gi.repository import Gio
entry = Gio.DesktopAppInfo.new_from_filename(sys.argv[1])
assert entry is not None
assert entry.launch([], None)
marker = Path(sys.argv[2]).parent / 'launched'
for _ in range(100):
    if marker.exists():
        break
    time.sleep(0.02)
assert marker.exists()
''', str(desktop), str(executable)], check=True)
