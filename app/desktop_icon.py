"""App logo paths for the desktop window and packaged binaries."""

from __future__ import annotations

import os
import shutil
import struct
import sys
import tempfile
from pathlib import Path

# GNOME Shell looks up this id in the desktop-file list. A window with no
# matching entry gets the generic gear icon, even if GTK has a window icon.
APP_ID = 'br.wsj.AegisKeePass'


def logo_png_path() -> Path:
    """Return the bundled logo, from the PyInstaller extract dir or the repo."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        root = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        root = Path(__file__).resolve().parents[1]
    return root / 'app' / 'static' / 'img' / 'logo.png'


def png_to_ico(png: bytes) -> bytes:
    """Wrap a 256×256 PNG in a Vista-style ICO (Windows window and exe icons)."""
    header = struct.pack('<HHH', 0, 1, 1)
    # Width and height 0 mean 256 pixels.
    entry = struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(png), 22)
    return header + entry + png


def png_to_icns(png: bytes) -> bytes:
    """Wrap a 256×256 PNG as an ic08 Apple icon (macOS app bundle)."""
    chunk = b'ic08' + struct.pack('>I', 8 + len(png)) + png
    return b'icns' + struct.pack('>I', 8 + len(chunk)) + chunk


def _data_home() -> Path:
    configured = os.environ.get('XDG_DATA_HOME', '').strip()
    if configured:
        return Path(configured)
    return Path.home() / '.local' / 'share'


def _desktop_exec_arg(value: str) -> str:
    """Quote one Exec argument (desktop-entry syntax, not shell syntax)."""
    # Percent introduces field codes even inside quotes. Backslashes must
    # survive both desktop string unescaping and Exec argument unescaping.
    value = value.replace('%', '%%')
    value = value.replace('\\', '\\\\\\\\')
    for char in ('"', '`', '$'):
        value = value.replace(char, '\\\\' + char)
    value = value.replace('\n', r'\n').replace('\r', r'\r').replace('\t', r'\t')
    return f'"{value}"'


def _launch_command() -> str:
    # The AppImage runtime sets APPIMAGE to the file the user launched.
    # sys.executable is the temporary mount and disappears when the app exits.
    appimage = os.environ.get('APPIMAGE', '').strip()
    if appimage:
        return _desktop_exec_arg(appimage)
    if getattr(sys, 'frozen', False):
        return _desktop_exec_arg(sys.executable)
    entry = Path(__file__).resolve().parents[1] / 'desktop_main.py'
    return f'{_desktop_exec_arg(sys.executable)} {_desktop_exec_arg(str(entry))}'


def install_linux_desktop_entry() -> Path | None:
    """Publish a desktop entry so GNOME uses the logo for this window.

    The entry is written under ``XDG_DATA_HOME/applications`` before the
    window opens. ``Icon`` is a stable copy of the logo, not the PyInstaller
    extract directory.
    """
    if not sys.platform.startswith('linux'):
        return None
    source = logo_png_path()
    if not source.is_file():
        return None

    data_home = _data_home()
    icon_dest = data_home / 'aegis-keepass' / 'logo.png'
    icon_dest.parent.mkdir(parents=True, exist_ok=True)
    if not icon_dest.is_file() or icon_dest.read_bytes() != source.read_bytes():
        shutil.copyfile(source, icon_dest)

    desktop = data_home / 'applications' / f'{APP_ID}.desktop'
    desktop.parent.mkdir(parents=True, exist_ok=True)
    # AppManager and other integrators own this file when they create it.
    # Register a fallback for window identity, but never replace their launch
    # command, version, update metadata, or uninstall action.
    if desktop.exists():
        return desktop
    contents = (
        '[Desktop Entry]\n'
        'Type=Application\n'
        'Name=Aegis-KeePass OTP Sync\n'
        f'Exec={_launch_command()}\n'
        f'Icon={icon_dest}\n'
        f'StartupWMClass={APP_ID}\n'
        'Terminal=false\n'
        'Categories=Utility;\n'
    )
    desktop.write_text(contents, encoding='utf-8')
    return desktop


def use_linux_app_id() -> None:
    """Make the GTK window's Wayland app id match the desktop entry."""
    if not sys.platform.startswith('linux'):
        return
    import gi

    gi.require_version('Gtk', '3.0')
    from gi.repository import Gio, GLib

    import webview.platforms.gtk as gtk_backend

    GLib.set_prgname(APP_ID)
    original = gtk_backend.gtk.Application.new
    if getattr(original, '_aegis_wrapped', False):
        return

    def _new(app_id, flags):
        if not app_id:
            app_id = APP_ID
            flags = Gio.ApplicationFlags(int(flags) | int(Gio.ApplicationFlags.NON_UNIQUE))
        return original(app_id, flags)

    _new._aegis_wrapped = True
    gtk_backend.gtk.Application.new = _new


def window_icon_path() -> str | None:
    """Path pywebview can load on this platform, or None if the logo is missing."""
    png_path = logo_png_path()
    if not png_path.is_file():
        return None
    if sys.platform.startswith('win'):
        dest = Path(tempfile.gettempdir()) / 'aegis-keepass-logo.ico'
        dest.write_bytes(png_to_ico(png_path.read_bytes()))
        return str(dest)
    return str(png_path)
