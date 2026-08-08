"""Detect host OS light/dark preference for the desktop shell.

WebKitGTK (pywebview on Linux/WSL) often ignores the OS appearance for
``prefers-color-scheme``, so the UI resolves ``System`` from this helper
instead of relying on ``matchMedia`` alone.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Literal, Optional

SystemTheme = Literal['light', 'dark']


def _is_wsl() -> bool:
    if os.environ.get('WSL_DISTRO_NAME') or os.environ.get('WSL_INTEROP'):
        return True
    try:
        with open('/proc/sys/kernel/osrelease', encoding='utf-8') as fh:
            return 'microsoft' in fh.read().lower()
    except OSError:
        return False


def _windows_apps_use_light_theme() -> Optional[bool]:
    """Return True if Windows apps prefer light, False if dark, else None."""
    if sys.platform == 'win32':
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
            ) as key:
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                return bool(int(value))
        except OSError:
            return None

    if not _is_wsl():
        return None

    reg = '/mnt/c/Windows/System32/reg.exe'
    if not os.path.isfile(reg):
        return None
    try:
        proc = subprocess.run(
            [
                reg,
                'query',
                r'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
                '/v',
                'AppsUseLightTheme',
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    match = re.search(r'AppsUseLightTheme\s+REG_DWORD\s+0x([0-9a-fA-F]+)', proc.stdout)
    if not match:
        return None
    return int(match.group(1), 16) != 0


def _linux_color_scheme() -> Optional[SystemTheme]:
    try:
        proc = subprocess.run(
            ['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip().strip("'\"")
    if value == 'prefer-dark':
        return 'dark'
    if value == 'prefer-light':
        return 'light'
    return None


def _macos_color_scheme() -> Optional[SystemTheme]:
    try:
        proc = subprocess.run(
            ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode == 0 and 'dark' in proc.stdout.strip().lower():
        return 'dark'
    # Missing key / non-zero usually means light.
    if proc.returncode != 0:
        return 'light'
    return 'light'


def detect_system_theme() -> Optional[SystemTheme]:
    """Return ``'dark'`` / ``'light'`` when known, else ``None``."""
    if sys.platform == 'darwin':
        return _macos_color_scheme()

    if sys.platform == 'win32':
        uses_light = _windows_apps_use_light_theme()
        if uses_light is None:
            return None
        return 'light' if uses_light else 'dark'

    if sys.platform.startswith('linux'):
        # WSL: Windows appearance is what the user set; Linux gsettings is often default.
        if _is_wsl():
            uses_light = _windows_apps_use_light_theme()
            if uses_light is not None:
                return 'light' if uses_light else 'dark'
        return _linux_color_scheme()

    return None


def apply_gtk_prefer_dark(prefer_dark: bool) -> None:
    """Hint GTK/WebKitGTK so ``prefers-color-scheme`` can match the OS."""
    try:
        import gi

        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk

        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property('gtk-application-prefer-dark-theme', bool(prefer_dark))
    except Exception:
        pass


def prepare_desktop_system_theme() -> SystemTheme:
    """Detect OS theme, export ``AK_SYSTEM_THEME``, and align GTK when possible.

    Falls back to dark when the host preference cannot be detected (WebKitGTK
    otherwise often reports light incorrectly).
    """
    theme = detect_system_theme() or 'dark'
    os.environ['AK_SYSTEM_THEME'] = theme
    apply_gtk_prefer_dark(theme == 'dark')
    return theme


def system_theme_from_environ() -> Optional[SystemTheme]:
    value = os.environ.get('AK_SYSTEM_THEME', '').strip().lower()
    if value in ('light', 'dark'):
        return value  # type: ignore[return-value]
    return None
