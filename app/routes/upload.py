"""Upload landing page and file ingestion."""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, render_template, request

from aegis_keepass_lib import (
    AegisDecryptor,
    AegisParser,
    CRYPTO_AVAILABLE,
    KeePassKdbx,
    PYKEEPASS_AVAILABLE,
)
from app.auth import get_session_store, session_required_api, set_session_cookie
from app.secure import EncryptedSpillStore, SecureBytes
from app.session import SessionData, SessionStore

bp = Blueprint('upload', __name__)


def _session() -> SessionData:
    return g.session_data


def _store_pending_upload(
    session: SessionData,
    aegis_bytes: bytes,
    keepass_bytes: bytes,
    keyfile_bytes: bytes | None,
) -> None:
    """Hold uploaded file bytes in memory or encrypted spill until processing."""
    max_in_memory = current_app.config['MAX_IN_MEMORY_UPLOAD_BYTES']
    combined_size = len(aegis_bytes) + len(keepass_bytes) + len(keyfile_bytes or b'')

    if combined_size > max_in_memory:
        spill = EncryptedSpillStore.create()
        session.spill_store = spill
        aegis_path = spill.store('aegis', aegis_bytes)
        keepass_path = spill.store('keepass', keepass_bytes)
        session.pending_aegis = spill.load(aegis_path)
        session.pending_keepass = spill.load(keepass_path)
        if keyfile_bytes:
            keyfile_path = spill.store('keyfile', keyfile_bytes)
            session.pending_keyfile = spill.load(keyfile_path)
    else:
        session.pending_aegis = SecureBytes(aegis_bytes, registry=session.wipe_registry)
        session.pending_keepass = SecureBytes(keepass_bytes, registry=session.wipe_registry)
        if keyfile_bytes:
            session.pending_keyfile = SecureBytes(
                keyfile_bytes,
                registry=session.wipe_registry,
            )


@bp.route('/')
def index():
    return render_template('upload.html')


@bp.route('/api/upload', methods=['POST'])
def api_upload():
    if not CRYPTO_AVAILABLE:
        return jsonify({'error': 'cryptography library is required'}), 500
    if not PYKEEPASS_AVAILABLE:
        return jsonify({'error': 'pykeepass library is required'}), 500

    aegis_file = request.files.get('aegis')
    keepass_file = request.files.get('keepass')
    keyfile = request.files.get('keyfile')
    aegis_password_raw = request.form.get('aegis_password', '')
    keepass_password_raw = request.form.get('keepass_password', '')

    if not aegis_file or not keepass_file:
        return jsonify({'error': 'Both Aegis backup and KeePass database files are required'}), 400
    if not aegis_password_raw:
        return jsonify({'error': 'Aegis backup password is required'}), 400
    if not keepass_password_raw:
        return jsonify({'error': 'KeePass master password is required'}), 400

    aegis_bytes = aegis_file.read()
    keepass_bytes = keepass_file.read()
    keyfile_bytes = keyfile.read() if keyfile and keyfile.filename else None

    if not aegis_bytes or not keepass_bytes:
        empty_msg = (
            'Selected files cannot be empty'
            if current_app.config.get('DESKTOP_MODE')
            else 'Uploaded files cannot be empty'
        )
        return jsonify({'error': empty_msg}), 400

    if not AegisDecryptor.is_encrypted_bytes(aegis_bytes):
        return jsonify({'error': 'Only encrypted Aegis backup files are supported'}), 400

    if not KeePassKdbx.is_kdbx_bytes(keepass_bytes):
        return jsonify({'error': 'Only KeePass .kdbx database files are supported'}), 400

    store: SessionStore = get_session_store()
    session = store.create()

    try:
        session.aegis_password = SecureBytes(
            aegis_password_raw,
            registry=session.wipe_registry,
        )
        session.keepass_master_password = SecureBytes(
            keepass_password_raw,
            registry=session.wipe_registry,
        )
        if keyfile_bytes:
            session.keepass_keyfile_bytes = SecureBytes(
                keyfile_bytes,
                registry=session.wipe_registry,
            )
        _store_pending_upload(session, aegis_bytes, keepass_bytes, keyfile_bytes)
    except Exception:
        store.destroy(session.session_id)
        raise

    response = jsonify({
        'success': True,
        'step': 'upload',
        'message': (
            'Files loaded and validated'
            if current_app.config.get('DESKTOP_MODE')
            else 'Files uploaded and validated'
        ),
    })
    return set_session_cookie(response, session.session_id)


@bp.route('/api/upload/process', methods=['POST'])
@session_required_api
def api_upload_process():
    if not CRYPTO_AVAILABLE:
        return jsonify({'error': 'cryptography library is required'}), 500
    if not PYKEEPASS_AVAILABLE:
        return jsonify({'error': 'pykeepass library is required'}), 500

    step = (request.json or {}).get('step')
    session = _session()
    store = get_session_store()

    if step == 'decrypt_aegis':
        if session.pending_aegis is None:
            return jsonify({'error': 'Aegis backup not loaded in session'}), 400
        if session.aegis_password is None:
            return jsonify({'error': 'Aegis backup password not available'}), 400
        try:
            session.aegis_entries = AegisParser.parse_bytes(
                bytes(session.pending_aegis),
                session.aegis_password,
                registry=session.wipe_registry,
            )
        except ValueError as exc:
            store.destroy(session.session_id)
            return jsonify({'error': str(exc)}), 400
        except RuntimeError as exc:
            store.destroy(session.session_id)
            return jsonify({'error': str(exc)}), 400
        finally:
            # destroy() may already have wiped these on decrypt failure
            if session.pending_aegis is not None:
                session.pending_aegis.wipe()
                session.pending_aegis = None
            if session.aegis_password is not None:
                session.aegis_password.wipe()
                session.aegis_password = None

        return jsonify({
            'success': True,
            'step': 'decrypt_aegis',
            'message': 'Aegis backup decrypted',
            'aegis_count': len(session.aegis_entries),
        })

    if step == 'open_keepass':
        if session.pending_keepass is None:
            return jsonify({'error': 'KeePass database not loaded in session'}), 400
        if session.keepass_master_password is None:
            return jsonify({'error': 'KeePass master password not available'}), 400
        keyfile_data = (
            bytes(session.pending_keyfile)
            if session.pending_keyfile is not None
            else None
        )
        try:
            session.keepass_db = KeePassKdbx.open_bytes(
                bytes(session.pending_keepass),
                session.keepass_master_password,
                keyfile_bytes=keyfile_data,
            )
            session.keepass_entries, recycle_count = KeePassKdbx.entries_from_db(
                session.keepass_db,
            )
        except ValueError as exc:
            store.destroy(session.session_id)
            return jsonify({'error': str(exc)}), 400
        except RuntimeError as exc:
            store.destroy(session.session_id)
            return jsonify({'error': str(exc)}), 400
        finally:
            # destroy() may already have wiped these on open failure
            if session.pending_keepass is not None:
                session.pending_keepass.wipe()
                session.pending_keepass = None
            if session.pending_keyfile is not None:
                session.pending_keyfile.wipe()
                session.pending_keyfile = None

        return jsonify({
            'success': True,
            'step': 'open_keepass',
            'message': 'KeePass database opened',
            'keepass_count': len(session.keepass_entries),
            'recycle_bin_count': recycle_count,
        })

    if step == 'match':
        if not session.aegis_entries:
            return jsonify({'error': 'Aegis entries not loaded'}), 400
        if session.keepass_db is None:
            return jsonify({'error': 'KeePass database not opened'}), 400

        SessionStore.run_matcher(session)
        matched = sum(
            1 for a in session.match_assignments.values()
            if a.get('keepass_uuid')
        )
        return jsonify({
            'success': True,
            'step': 'match',
            'message': 'Matching complete',
            'redirect': '/review',
            'stats': {
                'aegis_total': len(session.aegis_entries),
                'keepass_total': len(session.keepass_entries),
                'matched': matched,
                'unmatched': len(session.aegis_entries) - matched,
            },
        })

    return jsonify({'error': f'Unknown processing step: {step}'}), 400
