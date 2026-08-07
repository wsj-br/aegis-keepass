"""Desktop entrypoint: Waitress + pywebview shell around the Flask app."""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request

# Must be set before create_app() so templates inject desktop_mode.
os.environ.setdefault('AK_DESKTOP', '1')


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _wait_for_health(port: int, timeout: float = 30.0) -> None:
    url = f'http://127.0.0.1:{port}/health'
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

    app = create_app()
    port = _free_loopback_port()
    server = create_server(app, host='127.0.0.1', port=port, threads=4)

    thread = threading.Thread(target=server.run, name='waitress', daemon=True)
    thread.start()
    _wait_for_health(port)

    api = DesktopApi(app)
    url = f'http://127.0.0.1:{port}/'
    webview.create_window(
        'Aegis-KeePass OTP Sync',
        url,
        js_api=api,
        width=1100,
        height=800,
        min_size=(800, 600),
    )
    webview.start()

    try:
        server.close()
    except Exception:
        pass
    # Ensure the daemon Waitress thread cannot keep the process alive.
    os._exit(0)
    return 0  # pragma: no cover


if __name__ == '__main__':
    sys.exit(main())
