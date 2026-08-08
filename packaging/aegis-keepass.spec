# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Aegis-KeePass desktop shell."""

from __future__ import annotations

import os
import re
import sys

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
)

block_cipher = None

# Spec lives in packaging/; repo root is one level up.
# SPEC is injected by PyInstaller when this file is executed.
SPECDIR = os.path.dirname(os.path.abspath(SPEC))
ROOT = os.path.abspath(os.path.join(SPECDIR, '..'))


def _read_version() -> str:
    path = os.path.join(ROOT, 'app', '_version.py')
    with open(path, encoding='utf-8') as fh:
        match = re.search(r'__version__\s*=\s*"([^"]+)"', fh.read())
    return match.group(1) if match else '0.0.0'


def _webview_platform_imports() -> list[str]:
    """Desktop backends only — skip webview.platforms.android (needs Kivy)."""
    if sys.platform == 'darwin':
        return ['webview.platforms.cocoa']
    if sys.platform == 'win32':
        return [
            'webview.platforms.edgechromium',
            'webview.platforms.winforms',
            'webview.platforms.mshtml',
            'webview.platforms.win32',
            'webview.platforms.cef',
        ]
    # Linux: GTK/WebKit only (Qt left out to avoid optional Qt pull-in).
    return ['webview.platforms.gtk']


# GNOME/GTK share trees — unused by the WebKit UI; use the host instead.
_DROP_DATA_PREFIXES = (
    'share/icons/',
    'share/locale/',
    'share/themes/',
    'share/mime/',
    'share/fontconfig/',
    'share/glib-2.0/',
)

# Host-provided GTK / WebKit / ICU stack (Linux). Keep cryptography/lxml/etc.
_DROP_LIB_PREFIXES = (
    'libatk-',
    'libcairo',
    'libepoxy',
    'libgdk-',
    'libgdk_pixbuf-',
    'libgio-',
    'libgirepository-',
    'libglib-',
    'libgmodule-',
    'libgobject-',
    'libgtk-',
    'libharfbuzz',
    'libicu',
    'libjavascriptcoregtk-',
    'libpango',
    'librsvg-',
    'libsoup-',
    'libwebkit2gtk-',
    'libwebkitgtk-',
)


def _norm(dest_name: str) -> str:
    return dest_name.replace('\\', '/')


def _drop_data(dest_name: str) -> bool:
    name = _norm(dest_name)
    if any(name == p.rstrip('/') or name.startswith(p) for p in _DROP_DATA_PREFIXES):
        return True
    # GI typelibs come from gir1.2-* packages on the host.
    if name.endswith('.typelib') or '/girepository-' in name or name.startswith('gi_typelibs/'):
        return True
    return False


def _drop_binary(dest_name: str) -> bool:
    base = os.path.basename(_norm(dest_name))
    return any(base.startswith(prefix) for prefix in _DROP_LIB_PREFIXES)


def _filter_toc(entries, drop_fn):
    kept = []
    removed = 0
    for entry in entries:
        dest = entry[0]
        if drop_fn(dest):
            removed += 1
            continue
        kept.append(entry)
    return kept, removed


APP_VERSION = _read_version()

datas = [
    (os.path.join(ROOT, 'app', 'templates'), os.path.join('app', 'templates')),
    (os.path.join(ROOT, 'app', 'static'), os.path.join('app', 'static')),
    (os.path.join(ROOT, 'LICENSE'), '.'),
    (os.path.join(ROOT, 'NOTICES'), '.'),
]
binaries = []
hiddenimports = [
    'aegis_keepass_lib',
    'app',
    'app.desktop_api',
    'app.system_theme',
    'app.routes.health',
    'app.routes.upload',
    'app.routes.review',
    'app.session',
    'app.secure',
    'app.auth',
    'pykeepass',
    'construct',
    'cryptography',
    'rapidfuzz',
    'waitress',
    'webview',
]

# Avoid collect_all('webview'): it walks platforms.android and warns without Kivy.
datas += collect_data_files('webview')
binaries += collect_dynamic_libs('webview')
hiddenimports += _webview_platform_imports()

for pkg in ('cryptography', 'pykeepass'):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# macOS universal2 when building on macOS with a universal2 Python.
target_arch = 'universal2' if sys.platform == 'darwin' else None

a = Analysis(
    [os.path.join(ROOT, 'desktop_main.py')],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # setuptools/pkg_resources are unused by the app; collecting them with
    # modern setuptools often breaks the frozen binary (missing top-level jaraco).
    excludes=['gunicorn', 'pkg_resources', 'setuptools'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Prefer host GTK/WebKit/ICU + icon themes (documented runtime deps on Linux).
a.datas, dropped_data = _filter_toc(a.datas, _drop_data)
a.binaries, dropped_bin = _filter_toc(a.binaries, _drop_binary)
print(
    f'Packaging trim: removed {dropped_data} data entries and '
    f'{dropped_bin} bundled native libs (icons/themes/GTK/ICU/WebKit).'
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='aegis-keepass',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='Aegis-KeePass OTP Sync.app',
        icon=None,
        bundle_identifier='br.wsj.aegis-keepass',
        info_plist={
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': APP_VERSION,
            'NSHighResolutionCapable': True,
        },
    )
