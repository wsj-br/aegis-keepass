"""Desktop entrypoint: Waitress + pywebview shell around the Flask app."""

from __future__ import annotations

import glob
import importlib
import importlib.util
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

# Must be set before create_app() so templates inject desktop_mode.
os.environ.setdefault('AK_DESKTOP', '1')


def _system_gi_dist() -> str | None:
    """Return dist-packages that contains PyGObject built for this interpreter."""
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


def _expose_system_gi() -> None:
    """Let a venv import distro ``gi`` without enabling every system package.

    Debian ``python3-gi`` lives in ``/usr/lib/python3/dist-packages``. A venv
    created without ``--system-site-packages`` cannot see it, so pywebview's
    GTK backend fails. Only the ``gi`` package is added to ``sys.path``.
    """
    if getattr(sys, 'frozen', False) or not sys.platform.startswith('linux'):
        return
    if importlib.util.find_spec('gi') is not None:
        return
    dist = _system_gi_dist()
    if dist is None:
        return
    vendor = tempfile.mkdtemp(prefix='aegis-keepass-gi-')
    os.symlink(os.path.join(dist, 'gi'), os.path.join(vendor, 'gi'))
    sys.path.insert(0, vendor)
    importlib.invalidate_caches()


def _prefer_host_gtk() -> None:
    """Use host GTK/WebKit typelibs after PyInstaller redirects them into the bundle.

    The Linux spec strips bundled typelibs, icon themes, and GTK/WebKit shared
    libraries. PyInstaller's GI runtime hooks still point ``GI_TYPELIB_PATH``
    and GTK path variables at that empty extract directory.
    """
    if not getattr(sys, 'frozen', False) or not sys.platform.startswith('linux'):
        return
    meipass = getattr(sys, '_MEIPASS', '')

    chosen: list[str] = []
    for pattern in (
        '/usr/lib/*/girepository-1.0',
        '/usr/lib/girepository-1.0',
        '/usr/lib64/girepository-1.0',
    ):
        for path in glob.glob(pattern):
            if not os.path.isdir(path) or '/gnome-shell/' in path:
                continue
            if path not in chosen:
                chosen.append(path)
    chosen.sort(
        key=lambda path: (
            not os.path.isfile(os.path.join(path, 'Gtk-3.0.typelib')),
            path,
        )
    )
    if chosen:
        os.environ['GI_TYPELIB_PATH'] = os.pathsep.join(chosen)

    for var in (
        'GTK_DATA_PREFIX',
        'GTK_EXE_PREFIX',
        'GTK_PATH',
        'PANGO_LIBDIR',
        'PANGO_SYSCONFDIR',
        'GIO_MODULE_DIR',
    ):
        value = os.environ.get(var, '')
        if meipass and value.startswith(meipass):
            os.environ.pop(var, None)

    pixbuf = os.environ.get('GDK_PIXBUF_MODULE_FILE', '')
    if not meipass or not pixbuf.startswith(meipass):
        return
    caches = glob.glob('/usr/lib/*/gdk-pixbuf-2.0/*/loaders.cache')
    caches.extend(glob.glob('/usr/lib/gdk-pixbuf-2.0/*/loaders.cache'))
    caches.extend(glob.glob('/usr/lib64/gdk-pixbuf-2.0/*/loaders.cache'))
    if caches:
        os.environ['GDK_PIXBUF_MODULE_FILE'] = caches[0]
    else:
        os.environ.pop('GDK_PIXBUF_MODULE_FILE', None)


_expose_system_gi()
_prefer_host_gtk()


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _wait_until_ready(port: int, timeout: float = 30.0) -> None:
    url = f'http://127.0.0.1:{port}/'
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        time.sleep(0.05)
    raise RuntimeError(f'Desktop server failed to become ready: {last_error}')


def main() -> int:
    import webview
    from waitress.server import create_server

    from app import create_app
    from app.desktop_api import DesktopApi
    from app.desktop_icon import (
        install_linux_desktop_entry,
        use_linux_app_id,
        window_icon_path,
    )
    from app.system_theme import prepare_desktop_system_theme

    # GNOME ignores a GTK window icon and shows a gear until a desktop entry
    # with the same app id exists. Publish that entry before the window opens.
    install_linux_desktop_entry()

    # WebKitGTK often reports light for prefers-color-scheme; align with the OS first.
    prepare_desktop_system_theme()

    app = create_app()
    port = _free_loopback_port()
    server = create_server(app, host='127.0.0.1', port=port, threads=4)

    thread = threading.Thread(target=server.run, name='waitress', daemon=True)
    thread.start()
    _wait_until_ready(port)

    api = DesktopApi(app)
    url = f'http://127.0.0.1:{port}/'
    webview.create_window(
        'Aegis-KeePass OTP Sync',
        url,
        js_api=api,
        width=750,
        height=660,
        min_size=(700, 600),
    )
    use_linux_app_id()
    webview.start(icon=window_icon_path())

    try:
        server.close()
    except Exception:
        pass
    # Ensure the daemon Waitress thread cannot keep the process alive.
    os._exit(0)
    return 0  # pragma: no cover


if __name__ == '__main__':
    sys.exit(main())
