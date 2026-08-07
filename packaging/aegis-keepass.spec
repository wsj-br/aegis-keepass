# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Aegis-KeePass desktop shell."""

from __future__ import annotations

import os
import re
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

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

for pkg in ('webview', 'cryptography', 'pykeepass'):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

hiddenimports += collect_submodules('webview.platforms')

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
    excludes=['gunicorn'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
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
