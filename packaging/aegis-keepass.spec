# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Aegis-KeePass desktop shell."""

from __future__ import annotations

import importlib
import importlib.util
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


def _linux_system_gi_dist() -> str | None:
    """Distro PyGObject matching this interpreter, if the venv cannot import it."""
    abi = f'cpython-{sys.version_info.major}{sys.version_info.minor}'
    candidates = [
        '/usr/lib/python3/dist-packages',
        f'/usr/lib/python{sys.version_info.major}/dist-packages',
        (
            f'/usr/lib/python{sys.version_info.major}.'
            f'{sys.version_info.minor}/dist-packages'
        ),
    ]
    for candidate in candidates:
        gi_dir = os.path.join(candidate, 'gi')
        if not os.path.isdir(gi_dir):
            continue
        for name in os.listdir(gi_dir):
            if name.startswith('_gi.') and abi in name:
                return candidate
    return None


def _link_system_gi(vendor: str, dist: str) -> None:
    os.makedirs(vendor, exist_ok=True)
    gi_link = os.path.join(vendor, 'gi')
    gi_target = os.path.join(dist, 'gi')
    if os.path.lexists(gi_link) and os.path.realpath(gi_link) != os.path.realpath(gi_target):
        os.remove(gi_link)
    if not os.path.lexists(gi_link):
        os.symlink(gi_target, gi_link)
    for name in os.listdir(dist):
        if not name.startswith('PyGObject-'):
            continue
        if not (name.endswith('.egg-info') or name.endswith('.dist-info')):
            continue
        link = os.path.join(vendor, name)
        target = os.path.join(dist, name)
        if os.path.lexists(link) and os.path.realpath(link) != os.path.realpath(target):
            os.remove(link)
        if not os.path.lexists(link):
            os.symlink(target, link)


def _linux_gi_pathex() -> list[str]:
    """Make ``gi`` importable to PyInstaller on Linux.

    A project venv does not see Debian ``python3-gi``. When the system copy
    matches this interpreter's ABI, expose only that package (plus its
    metadata, which PyInstaller's gi hook reads). CI Python builds that do
    not match the distro ABI should ``pip install 'PyGObject>=3.48,<3.52'``.
    """
    if not sys.platform.startswith('linux'):
        return []
    if importlib.util.find_spec('gi') is not None:
        return []
    dist = _linux_system_gi_dist()
    if dist is None:
        abi = f'cpython-{sys.version_info.major}{sys.version_info.minor}'
        raise SystemExit(
            'Linux desktop build: this Python cannot import gi (PyGObject), '
            f'and no system gi matching {abi} was found. Install '
            "PyGObject into this environment (pip install 'PyGObject>=3.48,<3.52') "
            'or install the distro python3-gi package built for the same Python.'
        )
    vendor = os.path.join(ROOT, 'build', 'gi-vendor')
    _link_system_gi(vendor, dist)
    sys.path.insert(0, vendor)
    importlib.invalidate_caches()
    print(f'Using system PyGObject from {dist}')
    return [vendor]


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
    # WebKit loads the host color-management library. A bundled copy can
    # require a newer glibc than the host (v0.2.2 required GLIBC_2.43).
    'liblcms2.so',
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
    'app.desktop_icon',
    'app.system_theme',
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
if sys.platform.startswith('linux'):
    # Frozen Linux builds must carry the gi extension. Typelibs stay on the host.
    hiddenimports += ['gi']

GI_PATHEX = _linux_gi_pathex()

for pkg in ('cryptography', 'pykeepass'):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# Native architecture of this interpreter (separate Intel and Apple Silicon builds).
target_arch = None

a = Analysis(
    [os.path.join(ROOT, 'desktop_main.py')],
    pathex=[ROOT, *GI_PATHEX],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    # Skip the full Adwaita/icon/locale collect. Those trees are dropped below
    # and the host GTK install provides them.
    hooksconfig={
        'gi': {
            'icons': [],
            'themes': [],
            'languages': [],
        },
    },
    runtime_hooks=[],
    # setuptools/pkg_resources are unused by the app; collecting them with
    # modern setuptools often breaks the frozen binary (missing top-level jaraco).
    excludes=['pkg_resources', 'setuptools'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Prefer host GTK/WebKit/ICU + icon themes (documented runtime deps on Linux).
dropped_data = dropped_bin = 0
if sys.platform.startswith('linux'):
    a.datas, dropped_data = _filter_toc(a.datas, _drop_data)
    a.binaries, dropped_bin = _filter_toc(a.binaries, _drop_binary)
print(
    f'Packaging trim: removed {dropped_data} data entries and '
    f'{dropped_bin} bundled native libs (icons/themes/GTK/ICU/WebKit).'
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_icon_mod_spec = importlib.util.spec_from_file_location(
    'aegis_desktop_icon',
    os.path.join(ROOT, 'app', 'desktop_icon.py'),
)
_desktop_icon = importlib.util.module_from_spec(_icon_mod_spec)
_icon_mod_spec.loader.exec_module(_desktop_icon)
_logo_png = os.path.join(ROOT, 'app', 'static', 'img', 'logo.png')
_icon_dir = os.path.join(ROOT, 'build')
os.makedirs(_icon_dir, exist_ok=True)
_exe_icon = None
if sys.platform == 'win32':
    _exe_icon = os.path.join(_icon_dir, 'aegis-keepass.ico')
    with open(_logo_png, 'rb') as _logo_fh, open(_exe_icon, 'wb') as _icon_fh:
        _icon_fh.write(_desktop_icon.png_to_ico(_logo_fh.read()))
_bundle_icon = None
if sys.platform == 'darwin':
    _bundle_icon = os.path.join(_icon_dir, 'aegis-keepass.icns')
    with open(_logo_png, 'rb') as _logo_fh, open(_bundle_icon, 'wb') as _icon_fh:
        _icon_fh.write(_desktop_icon.png_to_icns(_logo_fh.read()))

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
    icon=_exe_icon,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='Aegis-KeePass OTP Sync.app',
        icon=_bundle_icon,
        bundle_identifier='br.wsj.aegis-keepass',
        info_plist={
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': APP_VERSION,
            'NSHighResolutionCapable': True,
        },
    )
