"""JS bridge API for the pywebview desktop shell."""

from __future__ import annotations

from typing import Any, Dict, Optional

import webview
from flask import Flask

from app.session import SessionStore
from app.system_theme import apply_gtk_prefer_dark


class DesktopApi:
    """Methods exposed to the web UI via ``window.pywebview.api``."""

    def __init__(self, app: Flask) -> None:
        self._app = app

    def set_prefer_dark(self, prefer_dark: bool = True) -> Dict[str, Any]:
        """Align GTK/WebKitGTK chrome with the UI light/dark resolution."""
        apply_gtk_prefer_dark(bool(prefer_dark))
        return {'ok': True, 'prefer_dark': bool(prefer_dark)}

    def download_merged(self, default_name: str = 'keepass-merged.kdbx') -> Dict[str, Any]:
        """Save the merged database via a native Save dialog, then wipe the session."""
        store: SessionStore = self._app.extensions['session_store']
        session = store.find_with_pending_download()
        if session is None or session.pending_download is None:
            return {'error': 'Merged database is not ready. Run save steps first.'}

        windows = webview.windows
        if not windows:
            return {'error': 'No desktop window available for Save dialog'}

        result = windows[0].create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=default_name or 'keepass-merged.kdbx',
        )
        if not result:
            return {'error': 'Save cancelled'}

        path: Optional[str]
        if isinstance(result, (list, tuple)):
            path = result[0] if result else None
        else:
            path = str(result)
        if not path:
            return {'error': 'Save cancelled'}

        summary = dict(session.save_summary or {})
        kdbx_bytes = bytes(session.pending_download)
        session_id = session.session_id

        try:
            with open(path, 'wb') as fh:
                fh.write(kdbx_bytes)
        except OSError as exc:
            return {'error': f'Failed to write file: {exc}'}

        # Mirror /api/save/download: wipe only after a successful save.
        store.destroy(session_id)

        return {
            'success': True,
            'redirect': '/',
            'path': path,
            'summary': {
                'total': str(summary.get('total', 0)),
                'otp': str(summary.get('otp', 0)),
                'updated': str(summary.get('updated', 0)),
                'cleaned': str(summary.get('cleaned', 0)),
            },
        }
