"""Review workflow and match APIs."""

from __future__ import annotations

import io
import re
from typing import Dict, List, Optional

from flask import Blueprint, g, jsonify, render_template, send_file

from aegis_keepass_lib import (
    AegisEntry,
    EntryMatcher,
    KeePassEntry,
    KeePassKdbx,
    KeePassUpdater,
    MatchResult,
)
from app.auth import clear_session_cookie, get_session_store, require_session, session_required_api
from app.session import SessionData

bp = Blueprint('review', __name__)


def _session() -> SessionData:
    return g.session_data


def _get_aegis_entry(aegis_uuid: str) -> Optional[AegisEntry]:
    return next((e for e in _session().aegis_entries if e.uuid == aegis_uuid), None)


def _get_keepass_entry(keepass_uuid: str) -> Optional[KeePassEntry]:
    return next((e for e in _session().keepass_entries if e.uuid == keepass_uuid), None)


def _matchable_keepass_entries() -> List[KeePassEntry]:
    return KeePassKdbx.matchable_entries(_session().keepass_entries)


def _assignment_for_aegis(aegis_uuid: str) -> Optional[Dict]:
    return _session().match_assignments.get(aegis_uuid)


def _set_match_assignment(
    aegis_uuid: str,
    keepass_uuid: str,
    confidence: float,
    reason: str,
) -> None:
    session = _session()
    for other_uuid, assignment in session.match_assignments.items():
        if other_uuid != aegis_uuid and assignment.get('keepass_uuid') == keepass_uuid:
            session.match_assignments[other_uuid] = {
                'keepass_uuid': None,
                'confidence': 0.0,
                'reason': '',
                'source': 'manual',
            }

    session.match_assignments[aegis_uuid] = {
        'keepass_uuid': keepass_uuid,
        'confidence': confidence,
        'reason': reason,
        'source': 'manual',
    }


def _linked_aegis_for_keepass(keepass_uuid: str, exclude_aegis: Optional[str] = None) -> Optional[str]:
    for aegis_uuid, assignment in _session().match_assignments.items():
        if exclude_aegis and aegis_uuid == exclude_aegis:
            continue
        if assignment.get('keepass_uuid') == keepass_uuid:
            return aegis_uuid
    return None


def _linked_aegis_conflict_info(
    keepass_uuid: str,
    exclude_aegis: Optional[str] = None,
) -> Optional[Dict]:
    conflict_uuid = _linked_aegis_for_keepass(keepass_uuid, exclude_aegis)
    if not conflict_uuid:
        return None
    conflict_entry = _get_aegis_entry(conflict_uuid)
    if conflict_entry:
        return {
            'linked_aegis_uuid': conflict_uuid,
            'linked_aegis_display': conflict_entry.display_name,
            'linked_aegis_issuer': conflict_entry.issuer or '',
            'linked_aegis_name': conflict_entry.name or '',
        }
    return {
        'linked_aegis_uuid': conflict_uuid,
        'linked_aegis_display': conflict_uuid,
        'linked_aegis_issuer': '',
        'linked_aegis_name': '',
    }


def _is_modified(aegis_uuid: str) -> bool:
    session = _session()
    current = session.match_assignments.get(aegis_uuid, {})
    initial = session.initial_assignments.get(aegis_uuid, {})
    return current.get('keepass_uuid') != initial.get('keepass_uuid')


def _serialize_aegis_entry(aegis_entry: AegisEntry) -> Dict:
    assignment = _assignment_for_aegis(aegis_entry.uuid) or {}
    keepass_uuid = assignment.get('keepass_uuid')
    kp_entry = _get_keepass_entry(keepass_uuid) if keepass_uuid else None
    matched = keepass_uuid is not None

    confidence = assignment.get('confidence', 0.0)
    if confidence > 1.0:
        display_confidence = min(confidence / 10.0, 1.0)
    else:
        display_confidence = confidence

    return {
        'aegis_uuid': aegis_entry.uuid,
        'display': aegis_entry.display_name,
        'issuer': aegis_entry.issuer or '',
        'name': aegis_entry.name or '',
        'matched': matched,
        'keepass_uuid': keepass_uuid,
        'keepass_title': kp_entry.title if kp_entry else None,
        'keepass_has_otp': kp_entry.has_otp() if kp_entry else False,
        'confidence': display_confidence,
        'reason': assignment.get('reason', '') if matched else '',
        'source': assignment.get('source', 'auto'),
        'modified': _is_modified(aegis_entry.uuid),
    }


def _normalize_search(text: str) -> str:
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text.lower()).strip()


def _serialize_keepass_details(kp_entry: KeePassEntry) -> Dict:
    return {
        'uuid': kp_entry.uuid,
        'title': kp_entry.title,
        'location': kp_entry.location_display,
        'group_path': kp_entry.group_path or '',
        'username': kp_entry.username or '',
        'url': kp_entry.url or '',
        'notes': kp_entry.notes or '',
        'has_otp': kp_entry.has_otp(),
    }


def _serialize_aegis_details(aegis_entry: AegisEntry) -> Dict:
    assignment = _assignment_for_aegis(aegis_entry.uuid) or {}
    keepass_uuid = assignment.get('keepass_uuid')
    kp_entry = _get_keepass_entry(keepass_uuid) if keepass_uuid else None

    return {
        'uuid': aegis_entry.uuid,
        'display': aegis_entry.display_name,
        'issuer': aegis_entry.issuer or '',
        'name': aegis_entry.name or '',
        'algo': aegis_entry.algo,
        'digits': aegis_entry.digits,
        'period': aegis_entry.period,
        'entry_type': aegis_entry.entry_type,
        'matched': keepass_uuid is not None,
        'keepass_title': kp_entry.title if kp_entry else '',
        'match_reason': assignment.get('reason', '') if keepass_uuid else '',
    }


def _excluded_keepass_uuids_for_suggest(aegis_uuid: str) -> set:
    excluded = set()
    for other_uuid, assignment in _session().match_assignments.items():
        if other_uuid == aegis_uuid:
            continue
        kp_uuid = assignment.get('keepass_uuid')
        if kp_uuid:
            excluded.add(kp_uuid)
    return excluded


@bp.route('/review')
@require_session
def review_page():
    return render_template('review.html')


@bp.route('/api/aegis-entries')
@session_required_api
def api_aegis_entries():
    from flask import request

    status = request.args.get('status', 'all')
    query = _normalize_search(request.args.get('q', ''))

    entries = []
    for aegis_entry in _session().aegis_entries:
        row = _serialize_aegis_entry(aegis_entry)
        if status == 'matched' and not row['matched']:
            continue
        if status == 'unmatched' and row['matched']:
            continue
        if query:
            haystack = _normalize_search(
                f"{row['display']} {row['issuer']} {row['name']}"
            )
            if query not in haystack:
                continue
        entries.append(row)

    entries.sort(key=lambda row: row['display'].casefold())

    matched_count = sum(
        1 for a in _session().match_assignments.values()
        if a.get('keepass_uuid')
    )
    total = len(_session().aegis_entries)

    return jsonify({
        'entries': entries,
        'stats': {
            'total': total,
            'matched': matched_count,
            'unmatched': total - matched_count,
        },
    })


@bp.route('/api/keepass/search')
@session_required_api
def api_keepass_search():
    from flask import request

    query = _normalize_search(request.args.get('q', ''))
    limit = min(int(request.args.get('limit', 25)), 100)
    offset = max(int(request.args.get('offset', 0)), 0)
    exclude_aegis = request.args.get('exclude_aegis')

    results = []
    for kp_entry in _matchable_keepass_entries():
        haystack = _normalize_search(
            f"{kp_entry.title} {kp_entry.username or ''} {kp_entry.url or ''}"
        )
        if query and query not in haystack:
            continue

        linked = _linked_aegis_conflict_info(kp_entry.uuid, exclude_aegis)
        row = {
            'uuid': kp_entry.uuid,
            'title': kp_entry.title,
            'username': kp_entry.username or '',
            'url': kp_entry.url or '',
            'has_otp': kp_entry.has_otp(),
            'linked_aegis_uuid': linked['linked_aegis_uuid'] if linked else None,
        }
        if linked:
            row.update(linked)
        results.append(row)

    results.sort(key=lambda r: r['title'].lower())
    total = len(results)
    return jsonify({
        'results': results[offset:offset + limit],
        'total': total,
        'limit': limit,
        'offset': offset,
    })


@bp.route('/api/keepass/entry')
@session_required_api
def api_keepass_entry():
    from flask import request

    keepass_uuid = request.args.get('uuid')
    if not keepass_uuid:
        return jsonify({'error': 'Missing uuid'}), 400

    kp_entry = _get_keepass_entry(keepass_uuid)
    if not kp_entry:
        return jsonify({'error': 'Unknown KeePass entry'}), 404

    return jsonify(_serialize_keepass_details(kp_entry))


@bp.route('/api/aegis/entry')
@session_required_api
def api_aegis_entry():
    from flask import request

    aegis_uuid = request.args.get('uuid')
    if not aegis_uuid:
        return jsonify({'error': 'Missing uuid'}), 400

    aegis_entry = _get_aegis_entry(aegis_uuid)
    if not aegis_entry:
        return jsonify({'error': 'Unknown Aegis entry'}), 404

    return jsonify(_serialize_aegis_details(aegis_entry))


@bp.route('/api/keepass/suggest', methods=['POST'])
@session_required_api
def api_keepass_suggest():
    from flask import request

    data = request.json or {}
    aegis_uuid = data.get('aegis_uuid')
    confirm = data.get('confirm', False)

    if not aegis_uuid:
        return jsonify({'error': 'Missing aegis_uuid'}), 400

    if aegis_uuid not in _session().match_assignments:
        return jsonify({'error': 'Unknown Aegis entry'}), 404

    aegis_entry = _get_aegis_entry(aegis_uuid)
    if not aegis_entry:
        return jsonify({'error': 'Unknown Aegis entry'}), 404

    matcher = EntryMatcher()
    excluded = _excluded_keepass_uuids_for_suggest(aegis_uuid)
    result = matcher.suggest_match(
        aegis_entry,
        _matchable_keepass_entries(),
        excluded_keepass_uuids=excluded,
    )

    if not result:
        return jsonify({'error': 'No suggestion found'}), 404

    keepass_uuid = result.keepass_entry.uuid
    conflict = _linked_aegis_conflict_info(keepass_uuid, exclude_aegis=aegis_uuid)
    if conflict and not confirm:
        return jsonify({
            'error': 'conflict',
            'message': 'Suggested KeePass entry is linked to another Aegis entry',
            **conflict,
            'suggestion': {
                'keepass_uuid': keepass_uuid,
                'keepass_title': result.keepass_entry.title,
                'confidence': result.confidence,
                'reason': result.match_reason,
            },
        }), 409

    _set_match_assignment(
        aegis_uuid,
        keepass_uuid,
        result.confidence,
        result.match_reason,
    )

    display_confidence = result.confidence
    if display_confidence > 1.0:
        display_confidence = min(display_confidence / 10.0, 1.0)

    return jsonify({
        'success': True,
        'entry': _serialize_aegis_entry(aegis_entry),
        'suggestion': {
            'keepass_uuid': keepass_uuid,
            'keepass_title': result.keepass_entry.title,
            'confidence': display_confidence,
            'reason': result.match_reason,
        },
    })


@bp.route('/api/match', methods=['PUT'])
@session_required_api
def api_set_match():
    from flask import request

    data = request.json or {}
    aegis_uuid = data.get('aegis_uuid')
    keepass_uuid = data.get('keepass_uuid')
    confirm = data.get('confirm', False)

    if not aegis_uuid or not keepass_uuid:
        return jsonify({'error': 'Missing UUIDs'}), 400

    if aegis_uuid not in _session().match_assignments:
        return jsonify({'error': 'Unknown Aegis entry'}), 404

    kp_entry = _get_keepass_entry(keepass_uuid)
    if not kp_entry:
        return jsonify({'error': 'Unknown KeePass entry'}), 404
    if not kp_entry.is_matchable:
        return jsonify({'error': 'Cannot match history or recycle bin entries'}), 400

    conflict = _linked_aegis_conflict_info(keepass_uuid, exclude_aegis=aegis_uuid)
    if conflict and not confirm:
        return jsonify({
            'error': 'conflict',
            'message': 'KeePass entry is already linked to another Aegis entry',
            **conflict,
        }), 409

    _set_match_assignment(aegis_uuid, keepass_uuid, 1.0, 'Manual match')

    aegis_entry = _get_aegis_entry(aegis_uuid)
    return jsonify({
        'success': True,
        'entry': _serialize_aegis_entry(aegis_entry),
    })


@bp.route('/api/match', methods=['DELETE'])
@session_required_api
def api_clear_match():
    from flask import request

    data = request.json or {}
    aegis_uuid = data.get('aegis_uuid')

    if not aegis_uuid:
        return jsonify({'error': 'Missing aegis_uuid'}), 400

    if aegis_uuid not in _session().match_assignments:
        return jsonify({'error': 'Unknown Aegis entry'}), 404

    _session().match_assignments[aegis_uuid] = {
        'keepass_uuid': None,
        'confidence': 0.0,
        'reason': '',
        'source': 'manual',
    }

    aegis_entry = _get_aegis_entry(aegis_uuid)
    return jsonify({
        'success': True,
        'entry': _serialize_aegis_entry(aegis_entry),
    })


@bp.route('/api/save', methods=['POST'])
@session_required_api
def api_save():
    session = _session()
    if session.keepass_db is None:
        return jsonify({'error': 'No KeePass data loaded'}), 400

    updater = KeePassUpdater(session.keepass_db)
    cleaned_count = 0
    updated_count = 0

    current_by_aegis = {
        uuid: a.get('keepass_uuid')
        for uuid, a in session.match_assignments.items()
    }
    initial_by_aegis = {
        uuid: a.get('keepass_uuid')
        for uuid, a in session.initial_assignments.items()
    }

    cleanup_pairs = set()

    for aegis_uuid, initial_kp in initial_by_aegis.items():
        current_kp = current_by_aegis.get(aegis_uuid)
        if initial_kp and initial_kp != current_kp:
            cleanup_pairs.add((initial_kp, aegis_uuid))

    for aegis_uuid, current_kp in current_by_aegis.items():
        if current_kp is None:
            initial_kp = initial_by_aegis.get(aegis_uuid)
            if initial_kp:
                cleanup_pairs.add((initial_kp, aegis_uuid))

    for kp_entry in session.keepass_entries:
        if not kp_entry.is_matchable:
            continue
        linked_uuid = kp_entry.get_aegis_uuid()
        if not linked_uuid:
            continue
        assigned_kp = current_by_aegis.get(linked_uuid)
        if assigned_kp != kp_entry.uuid:
            cleanup_pairs.add((kp_entry.uuid, linked_uuid))

    for keepass_uuid, aegis_uuid in cleanup_pairs:
        kp_entry = _get_keepass_entry(keepass_uuid)
        if kp_entry and kp_entry.is_matchable:
            changes = updater.remove_aegis_link(kp_entry, aegis_uuid)
            if changes['marker_removed'] or changes['fields_removed']:
                cleaned_count += 1

    for aegis_uuid, assignment in session.match_assignments.items():
        keepass_uuid = assignment.get('keepass_uuid')
        if not keepass_uuid:
            continue

        aegis_entry = _get_aegis_entry(aegis_uuid)
        kp_entry = _get_keepass_entry(keepass_uuid)
        if not aegis_entry or not kp_entry:
            continue

        match = MatchResult(
            aegis_entry=aegis_entry,
            keepass_entry=kp_entry,
            confidence=assignment.get('confidence', 1.0),
            match_reason=assignment.get('reason', 'Manual match'),
        )
        changes = updater.apply_match(match)
        if changes['fields_added'] or changes['fields_updated'] or changes['notes_updated']:
            updated_count += 1

    matchable_entries = KeePassKdbx.matchable_entries(session.keepass_entries)
    total_entries = len(matchable_entries)
    otp_entries = sum(1 for e in matchable_entries if e.has_otp())

    kdbx_bytes = updater.save_bytes()
    unmatched_count = sum(
        1 for a in session.match_assignments.values()
        if not a.get('keepass_uuid')
    )

    session_id = session.session_id
    store = get_session_store()

    def _wipe_after_send():
        store.destroy(session_id)

    response = send_file(
        io.BytesIO(kdbx_bytes),
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name='keepass-merged.kdbx',
    )
    response.call_on_close(_wipe_after_send)
    response.headers['X-Updated-Count'] = str(updated_count)
    response.headers['X-Cleaned-Count'] = str(cleaned_count)
    response.headers['X-Unmatched-Count'] = str(unmatched_count)
    response.headers['X-Total-Entries'] = str(total_entries)
    response.headers['X-Otp-Entries'] = str(otp_entries)
    return clear_session_cookie(response)


@bp.route('/api/session/end', methods=['POST'])
@session_required_api
def api_session_end():
    session_id = _session().session_id
    get_session_store().destroy(session_id)
    response = jsonify({'success': True, 'redirect': '/'})
    return clear_session_cookie(response)
