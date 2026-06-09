#!/usr/bin/env python3
"""
Aegis-KeePass OTP Sync — Web Interface

Import OTP secrets from Aegis into KeePass: match entries in the browser,
apply OTP fields to matched KeePass entries, and save a merged XML file.

Usage:
    python3 aegis_keepass_web.py --aegis aegis-backup.json --keepass keepass.xml
    python3 aegis_keepass_web.py --aegis aegis-backup.json --keepass keepass.xml --password-file pass.txt
    python3 aegis_keepass_web.py   # prompts for missing files and password interactively

Then open http://localhost:5000 in your browser.
"""

import argparse
import copy
import curses
import getpass
import logging
import os
import sys
import subprocess
import shlex
import threading
import time
import socket
from pathlib import Path
import re
from typing import List, Dict, Optional

from flask import Flask, render_template_string, request, jsonify

from aegis_keepass_lib import (
    AegisParser, KeePassParser, EntryMatcher,
    KeePassUpdater, AegisEntry, KeePassEntry, MatchResult,
    AegisDecryptor, CRYPTO_AVAILABLE
)


app = Flask(__name__)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

_shutdown_lock = threading.Lock()
_shutdown_scheduled = False

app_data = {
    'aegis_entries': [],
    'keepass_entries': [],
    'tree': None,
    'match_assignments': {},
    'initial_assignments': {},
    'keepass_path': None,
    'output_path': None,
}


def _schedule_server_shutdown(shutdown_func=None) -> None:
    """Stop the embedded Werkzeug server (idempotent)."""
    global _shutdown_scheduled
    with _shutdown_lock:
        if _shutdown_scheduled:
            return
        _shutdown_scheduled = True

    def _shutdown() -> None:
        time.sleep(0.15)
        print("\nStopping web server...")
        if shutdown_func is not None:
            shutdown_func()
        else:
            os._exit(0)

    threading.Thread(target=_shutdown, daemon=True).start()


def _get_aegis_entry(aegis_uuid: str) -> Optional[AegisEntry]:
    return next((e for e in app_data['aegis_entries'] if e.uuid == aegis_uuid), None)


def _get_keepass_entry(keepass_uuid: str) -> Optional[KeePassEntry]:
    return next((e for e in app_data['keepass_entries'] if e.uuid == keepass_uuid), None)


def _matchable_keepass_entries() -> List[KeePassEntry]:
    return KeePassParser.matchable_entries(app_data['keepass_entries'])


def _assignment_for_aegis(aegis_uuid: str) -> Optional[Dict]:
    return app_data['match_assignments'].get(aegis_uuid)


def _set_match_assignment(
    aegis_uuid: str,
    keepass_uuid: str,
    confidence: float,
    reason: str,
) -> None:
    """Assign a KeePass entry to an Aegis entry, clearing conflicting assignments."""
    for other_uuid, assignment in app_data['match_assignments'].items():
        if other_uuid != aegis_uuid and assignment.get('keepass_uuid') == keepass_uuid:
            app_data['match_assignments'][other_uuid] = {
                'keepass_uuid': None,
                'confidence': 0.0,
                'reason': '',
                'source': 'manual',
            }

    app_data['match_assignments'][aegis_uuid] = {
        'keepass_uuid': keepass_uuid,
        'confidence': confidence,
        'reason': reason,
        'source': 'manual',
    }


def _linked_aegis_for_keepass(keepass_uuid: str, exclude_aegis: Optional[str] = None) -> Optional[str]:
    for aegis_uuid, assignment in app_data['match_assignments'].items():
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
    current = app_data['match_assignments'].get(aegis_uuid, {})
    initial = app_data['initial_assignments'].get(aegis_uuid, {})
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


def _init_match_assignments(matches, unmatched):
    assignments = {}
    for entry in app_data['aegis_entries']:
        assignments[entry.uuid] = {
            'keepass_uuid': None,
            'confidence': 0.0,
            'reason': '',
            'source': 'auto',
        }

    for match in matches:
        assignments[match.aegis_entry.uuid] = {
            'keepass_uuid': match.keepass_entry.uuid,
            'confidence': match.confidence,
            'reason': match.match_reason,
            'source': 'auto',
        }

    app_data['match_assignments'] = assignments
    app_data['initial_assignments'] = copy.deepcopy(assignments)


def _normalize_search(text: str) -> str:
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text.lower()).strip()


@app.route('/')
def index():
    return render_template_string(ENTRIES_TEMPLATE)


@app.route('/api/aegis-entries')
def api_aegis_entries():
    status = request.args.get('status', 'all')
    query = _normalize_search(request.args.get('q', ''))

    entries = []
    for aegis_entry in app_data['aegis_entries']:
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
        1 for a in app_data['match_assignments'].values()
        if a.get('keepass_uuid')
    )
    total = len(app_data['aegis_entries'])

    return jsonify({
        'entries': entries,
        'stats': {
            'total': total,
            'matched': matched_count,
            'unmatched': total - matched_count,
        },
    })


@app.route('/api/keepass/search')
def api_keepass_search():
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


@app.route('/api/keepass/entry')
def api_keepass_entry():
    keepass_uuid = request.args.get('uuid')
    if not keepass_uuid:
        return jsonify({'error': 'Missing uuid'}), 400

    kp_entry = _get_keepass_entry(keepass_uuid)
    if not kp_entry:
        return jsonify({'error': 'Unknown KeePass entry'}), 404

    return jsonify(_serialize_keepass_details(kp_entry))


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


@app.route('/api/aegis/entry')
def api_aegis_entry():
    aegis_uuid = request.args.get('uuid')
    if not aegis_uuid:
        return jsonify({'error': 'Missing uuid'}), 400

    aegis_entry = _get_aegis_entry(aegis_uuid)
    if not aegis_entry:
        return jsonify({'error': 'Unknown Aegis entry'}), 404

    return jsonify(_serialize_aegis_details(aegis_entry))


def _excluded_keepass_uuids_for_suggest(aegis_uuid: str) -> set:
    """KeePass entries assigned to other Aegis entries in the current session."""
    excluded = set()
    for other_uuid, assignment in app_data['match_assignments'].items():
        if other_uuid == aegis_uuid:
            continue
        kp_uuid = assignment.get('keepass_uuid')
        if kp_uuid:
            excluded.add(kp_uuid)
    return excluded


@app.route('/api/keepass/suggest', methods=['POST'])
def api_keepass_suggest():
    data = request.json or {}
    aegis_uuid = data.get('aegis_uuid')
    confirm = data.get('confirm', False)

    if not aegis_uuid:
        return jsonify({'error': 'Missing aegis_uuid'}), 400

    if aegis_uuid not in app_data['match_assignments']:
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


@app.route('/api/match', methods=['PUT'])
def api_set_match():
    data = request.json or {}
    aegis_uuid = data.get('aegis_uuid')
    keepass_uuid = data.get('keepass_uuid')
    confirm = data.get('confirm', False)

    if not aegis_uuid or not keepass_uuid:
        return jsonify({'error': 'Missing UUIDs'}), 400

    if aegis_uuid not in app_data['match_assignments']:
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


@app.route('/api/match', methods=['DELETE'])
def api_clear_match():
    data = request.json or {}
    aegis_uuid = data.get('aegis_uuid')

    if not aegis_uuid:
        return jsonify({'error': 'Missing aegis_uuid'}), 400

    if aegis_uuid not in app_data['match_assignments']:
        return jsonify({'error': 'Unknown Aegis entry'}), 404

    app_data['match_assignments'][aegis_uuid] = {
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


@app.route('/api/save', methods=['POST'])
def api_save():
    if not app_data['keepass_path'] or not app_data['tree']:
        return jsonify({'error': 'No KeePass file loaded'}), 400

    updater = KeePassUpdater(app_data['tree'])
    cleaned_count = 0
    updated_count = 0

    current_by_aegis = {
        uuid: a.get('keepass_uuid')
        for uuid, a in app_data['match_assignments'].items()
    }
    initial_by_aegis = {
        uuid: a.get('keepass_uuid')
        for uuid, a in app_data['initial_assignments'].items()
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

    for kp_entry in app_data['keepass_entries']:
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

    for aegis_uuid, assignment in app_data['match_assignments'].items():
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

    output_path = app_data.get('output_path', app_data['keepass_path'])
    updater.save(output_path)

    output_file = Path(output_path)
    abs_output = output_file.resolve()
    print(f"\nMerged file saved:")
    print(f"  Name: {output_file.name}")
    print(f"  Path: {abs_output}")

    app_data['initial_assignments'] = copy.deepcopy(app_data['match_assignments'])

    unmatched_count = sum(
        1 for a in app_data['match_assignments'].values()
        if not a.get('keepass_uuid')
    )

    return jsonify({
        'success': True,
        'output_path': str(abs_output),
        'output_name': output_file.name,
        'updated_count': updated_count,
        'cleaned_count': cleaned_count,
        'unmatched_count': unmatched_count,
    })


@app.route('/api/shutdown', methods=['POST', 'GET'])
def api_shutdown():
    _schedule_server_shutdown(request.environ.get('werkzeug.server.shutdown'))
    return '', 204


ENTRIES_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Aegis-KeePass Sync</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: system-ui, sans-serif; margin: 0; padding: 0; background: #f8f9fa; color: #333; }
        .header {
            position: sticky; top: 0; z-index: 100;
            background: #fff; border-bottom: 1px solid #ddd;
            padding: 16px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .header h1 { margin: 0 0 12px; font-size: 1.4em; }
        .toolbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
        .stats { display: flex; gap: 16px; font-size: 0.9em; color: #666; }
        .stats strong { color: #333; }
        .filters { display: flex; gap: 4px; }
        .filter-btn {
            padding: 6px 14px; border: 1px solid #ccc; background: #fff;
            border-radius: 6px; cursor: pointer; font-size: 0.9em;
        }
        .filter-btn.active { background: #0066cc; color: #fff; border-color: #0066cc; }
        .search-input {
            padding: 6px 12px; border: 1px solid #ccc; border-radius: 6px;
            font-size: 0.9em; min-width: 200px;
        }
        .btn {
            padding: 8px 18px; border: none; border-radius: 6px;
            cursor: pointer; font-size: 0.9em; font-weight: 500;
        }
        .btn-primary { background: #0066cc; color: #fff; }
        .btn-primary:hover { background: #0052a3; }
        .btn-secondary { background: #e9ecef; color: #333; }
        .btn-secondary:hover { background: #dee2e6; }
        .btn-danger { background: #dc3545; color: #fff; }
        .btn-danger:hover { background: #c82333; }
        .btn-sm { padding: 4px 10px; font-size: 0.85em; }
        .content { padding: 16px 24px; }
        table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
        th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }
        th { background: #f5f5f5; font-weight: 600; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.03em; color: #555; }
        tr.matched { background: #f0faf4; }
        tr.modified { border-left: 3px solid #ff9800; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: 500; }
        .badge-matched { background: #d4edda; color: #155724; }
        .badge-unmatched { background: #f8d7da; color: #721c24; }
        .badge-modified { background: #fff3cd; color: #856404; margin-left: 4px; }
        .confidence { background: #0066cc; color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
        .confidence-low { background: #ff9800; }
        .meta { color: #666; font-size: 0.85em; }
        .actions { display: flex; gap: 6px; flex-wrap: wrap; }
        .otp-badge { background: #ff9800; color: #fff; padding: 1px 6px; border-radius: 4px; font-size: 0.75em; }
        .kp-cell { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
        .info-kp-btn, .info-aegis-btn {
            background: transparent;
            border: none;
            padding: 0 2px;
            margin: 0;
            cursor: pointer;
            font-size: 1em;
            line-height: 1;
            opacity: 0.55;
            vertical-align: middle;
        }
        .info-kp-btn:hover, .info-aegis-btn:hover { opacity: 1; }
        .aegis-title-row { display: inline-flex; align-items: center; gap: 4px; }
        .empty { text-align: center; padding: 40px; color: #666; }
        .modal-overlay {
            display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.4);
            z-index: 200; align-items: center; justify-content: center;
        }
        #info-modal { z-index: 250; }
        #conflict-modal { z-index: 260; }
        .conflict-linked {
            margin: 12px 0;
            padding: 12px;
            background: #fff8e1;
            border: 1px solid #ffcc80;
            border-radius: 6px;
        }
        .conflict-linked strong { display: block; margin-bottom: 4px; }
        .modal-overlay.open { display: flex; }
        .modal {
            background: #fff; border-radius: 10px; width: 90%; max-width: 600px;
            max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 8px 30px rgba(0,0,0,0.2);
        }
        .modal-header { padding: 16px 20px; border-bottom: 1px solid #eee; }
        .modal-header h2 { margin: 0 0 8px; font-size: 1.1em; }
        .modal-actions { display: flex; gap: 8px; margin-bottom: 8px; }
        .search-result.suggested { border-color: #0066cc; background: #e8f0fe; }
        .modal-body { padding: 12px 20px; overflow-y: auto; flex: 1; }
        .modal-footer { padding: 12px 20px; border-top: 1px solid #eee; text-align: right; }
        .picker-footer { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
        .pagination { display: flex; align-items: center; gap: 10px; font-size: 0.9em; color: #666; }
        .pagination .btn:disabled { opacity: 0.45; cursor: not-allowed; }
        .search-result {
            display: flex; align-items: center; gap: 10px;
            padding: 10px; margin: 4px 0; border-radius: 6px; border: 1px solid #eee;
        }
        .search-result:hover { background: #f0f4ff; }
        .search-result.linked { border-color: #ff9800; background: #fff8e1; }
        .search-result .info { flex: 1; }
        .search-result .title { font-weight: 500; }
        .search-result .sub { font-size: 0.85em; color: #666; }
        .search-result .result-actions { display: flex; gap: 6px; flex-shrink: 0; }
        .detail-location { font-size: 1.05em; font-weight: 600; margin-bottom: 16px; line-height: 1.4; }
        .detail-field { margin-bottom: 14px; }
        .detail-label { font-weight: 600; font-size: 0.85em; color: #555; margin-bottom: 4px; }
        .detail-value { white-space: pre-wrap; word-break: break-word; }
        .detail-value.empty-field { color: #999; font-style: italic; }
        .toast {
            position: fixed; bottom: 24px; right: 24px; background: #333; color: #fff;
            padding: 12px 20px; border-radius: 8px; z-index: 300; display: none;
            max-width: 400px; font-size: 0.9em;
        }
        .toast.show { display: block; }
        .toast.success { background: #28a745; }
        .toast.error { background: #dc3545; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Aegis-KeePass OTP Sync</h1>
        <p class="meta" style="margin: -8px 0 12px;">Import OTP secrets · Match entries · Merge into KeePass</p>
        <div class="toolbar">
            <div class="stats" id="stats">
                <span>Total: <strong id="stat-total">-</strong></span>
                <span>Matched: <strong id="stat-matched">-</strong></span>
                <span>Unmatched: <strong id="stat-unmatched">-</strong></span>
            </div>
            <div class="filters">
                <button class="filter-btn active" data-status="all">All</button>
                <button class="filter-btn" data-status="matched">Matched</button>
                <button class="filter-btn" data-status="unmatched">Unmatched</button>
            </div>
            <input type="text" class="search-input" id="aegis-filter" placeholder="Filter Aegis entries...">
            <button class="btn btn-primary" id="save-btn">Save Merged File</button>
            <button class="btn btn-secondary" id="close-btn">Close</button>
        </div>
    </div>

    <div class="content">
        <table>
            <thead>
                <tr>
                    <th>Status</th>
                    <th>Aegis Entry</th>
                    <th>KeePass Entry</th>
                    <th>Match Info</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="entries-body">
                <tr><td colspan="5" class="empty">Loading...</td></tr>
            </tbody>
        </table>
    </div>

    <div class="modal-overlay" id="picker-modal">
        <div class="modal">
            <div class="modal-header">
                <h2 id="picker-title">Select KeePass Entry</h2>
                <div class="modal-actions">
                    <button class="btn btn-primary btn-sm" id="suggest-btn">Suggest</button>
                </div>
                <input type="text" class="search-input" id="keepass-search" placeholder="Search KeePass by title, username, URL..." style="width:100%;">
            </div>
            <div class="modal-body" id="search-results"></div>
            <div class="modal-footer picker-footer">
                <div class="pagination" id="search-pagination"></div>
                <button class="btn btn-secondary" onclick="closePicker()">Cancel</button>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="conflict-modal">
        <div class="modal">
            <div class="modal-header">
                <h2>Reassign KeePass entry?</h2>
            </div>
            <div class="modal-body" id="conflict-body"></div>
            <div class="modal-footer">
                <button class="btn btn-secondary" id="conflict-cancel-btn">Cancel</button>
                <button class="btn btn-danger" id="conflict-confirm-btn">Reassign anyway</button>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="info-modal">
        <div class="modal">
            <div class="modal-header">
                <h2 id="info-modal-title">Entry Details</h2>
            </div>
            <div class="modal-body" id="info-body"></div>
            <div class="modal-footer">
                <button class="btn btn-secondary" id="info-close-btn">Close</button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        let currentStatus = 'all';
        let aegisFilter = '';
        let pickerAegisUuid = null;
        let searchTimeout = null;
        let intentionalShutdown = false;

        function requestServerShutdown() {
            const payload = new Blob([], { type: 'application/octet-stream' });
            if (navigator.sendBeacon) {
                navigator.sendBeacon('/api/shutdown', payload);
            } else {
                fetch('/api/shutdown', { method: 'POST', keepalive: true });
            }
        }

        function showServerStopped() {
            document.querySelector('.header').innerHTML =
                '<h1>Aegis-KeePass OTP Sync</h1>'
                + '<p class="meta" style="margin: 8px 0 0;">Server stopped. You may close this tab.</p>';
            document.querySelector('.content').innerHTML = '';
        }
        let searchPage = 0;
        let searchTotal = 0;
        let keepassSearchQuery = '';
        const SEARCH_PAGE_SIZE = 25;

        function showToast(msg, type) {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.className = 'toast show ' + (type || '');
            setTimeout(() => { t.className = 'toast'; }, 5000);
        }

        function escHtml(s) {
            const d = document.createElement('div');
            d.textContent = s || '';
            return d.innerHTML;
        }

        function escAttr(s) {
            return (s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
        }

        async function loadEntries() {
            const params = new URLSearchParams({ status: currentStatus, q: aegisFilter });
            const resp = await fetch('/api/aegis-entries?' + params);
            const data = await resp.json();

            document.getElementById('stat-total').textContent = data.stats.total;
            document.getElementById('stat-matched').textContent = data.stats.matched;
            document.getElementById('stat-unmatched').textContent = data.stats.unmatched;

            const tbody = document.getElementById('entries-body');
            if (!data.entries.length) {
                tbody.innerHTML = '<tr><td colspan="5" class="empty">No entries found.</td></tr>';
                return;
            }

            tbody.innerHTML = data.entries.map(e => {
                const rowClass = (e.matched ? 'matched' : '') + (e.modified ? ' modified' : '');
                const statusBadge = e.matched
                    ? '<span class="badge badge-matched">Matched</span>'
                    : '<span class="badge badge-unmatched">Unmatched</span>';
                const modBadge = e.modified ? '<span class="badge badge-modified">Modified</span>' : '';

                let kpCell = '<span class="meta">—</span>';
                if (e.matched) {
                    kpCell = '<div class="kp-cell"><span>'
                        + escHtml(e.keepass_title)
                        + (e.keepass_has_otp ? ' <span class="otp-badge">OTP</span>' : '')
                        + '</span>'
                        + '<button type="button" class="info-kp-btn" data-uuid="' + e.keepass_uuid + '" title="Entry details" aria-label="Entry details">ℹ️</button>'
                        + '</div>';
                }

                let matchInfo = '<span class="meta">—</span>';
                if (e.matched && e.confidence > 0) {
                    const pct = Math.round(e.confidence * 100);
                    const cls = e.confidence < 0.8 ? ' confidence-low' : '';
                    matchInfo = '<span class="confidence' + cls + '">' + pct + '%</span> '
                        + '<span class="meta">' + escHtml(e.reason) + '</span>';
                }

                const selectLabel = e.matched ? 'Change' : 'Select';
                let actions = '<button class="btn btn-secondary btn-sm picker-btn" data-uuid="' + e.aegis_uuid + '" data-display="' + escAttr(e.display) + '">' + selectLabel + '</button>';
                if (e.matched) {
                    actions += ' <button class="btn btn-danger btn-sm clear-btn" data-uuid="' + e.aegis_uuid + '">Clear match</button>';
                }

                return '<tr class="' + rowClass.trim() + '" data-uuid="' + e.aegis_uuid + '">'
                    + '<td>' + statusBadge + modBadge + '</td>'
                    + '<td><div class="aegis-title-row"><strong>' + escHtml(e.display) + '</strong>'
                    + '<button type="button" class="info-aegis-btn" data-uuid="' + e.aegis_uuid + '" title="Entry details" aria-label="Entry details">ℹ️</button>'
                    + '</div>'
                    + '<div class="meta">' + escHtml(e.issuer) + ' / ' + escHtml(e.name) + '</div></td>'
                    + '<td>' + kpCell + '</td>'
                    + '<td>' + matchInfo + '</td>'
                    + '<td class="actions">' + actions + '</td>'
                    + '</tr>';
            }).join('');
        }

        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentStatus = btn.dataset.status;
                loadEntries();
            });
        });

        document.getElementById('aegis-filter').addEventListener('input', (e) => {
            aegisFilter = e.target.value;
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(loadEntries, 200);
        });

        function openPicker(aegisUuid, display) {
            pickerAegisUuid = aegisUuid;
            searchPage = 0;
            keepassSearchQuery = '';
            document.getElementById('picker-title').textContent = 'Select KeePass entry for: ' + display;
            document.getElementById('keepass-search').value = '';
            document.getElementById('search-results').innerHTML = '<p class="meta">Loading...</p>';
            document.getElementById('search-pagination').innerHTML = '';
            document.getElementById('picker-modal').classList.add('open');
            document.getElementById('keepass-search').focus();
            searchKeepass('');
        }

        function closePicker() {
            pickerAegisUuid = null;
            document.getElementById('picker-modal').classList.remove('open');
        }

        function detailField(label, value) {
            const cls = value ? 'detail-value' : 'detail-value empty-field';
            const text = value !== undefined && value !== null && value !== '' ? String(value) : '(empty)';
            return '<div class="detail-field"><div class="detail-label">' + label + '</div>'
                + '<div class="' + cls + '">' + escHtml(text) + '</div></div>';
        }

        function renderKeepassInfoBody(data) {
            const otpText = data.has_otp ? 'Configured' : 'Not configured';
            const otpClass = data.has_otp ? '' : ' empty-field';

            return '<div class="detail-location">' + escHtml(data.location) + '</div>'
                + detailField('username', data.username)
                + detailField('URL', data.url)
                + detailField('Notes', data.notes)
                + '<div class="detail-field"><div class="detail-label">OTP</div>'
                + '<div class="detail-value' + otpClass + '">' + otpText + '</div></div>';
        }

        function renderAegisInfoBody(data) {
            const matchText = data.matched
                ? data.keepass_title + (data.match_reason ? ' (' + data.match_reason + ')' : '')
                : '';

            return '<div class="detail-location">' + escHtml(data.display) + '</div>'
                + detailField('UUID', data.uuid)
                + detailField('issuer', data.issuer)
                + detailField('name', data.name)
                + detailField('algorithm', data.algo)
                + detailField('digits', data.digits)
                + detailField('period', data.period)
                + detailField('type', data.entry_type)
                + detailField('KeePass match', matchText);
        }

        async function showKeepassInfo(keepassUuid) {
            const resp = await fetch('/api/keepass/entry?uuid=' + encodeURIComponent(keepassUuid));
            const data = await resp.json();
            if (!resp.ok) {
                showToast(data.error || 'Failed to load entry details', 'error');
                return;
            }
            document.getElementById('info-modal-title').textContent = 'KeePass Entry Details';
            document.getElementById('info-body').innerHTML = renderKeepassInfoBody(data);
            document.getElementById('info-modal').classList.add('open');
        }

        async function showAegisInfo(aegisUuid) {
            const resp = await fetch('/api/aegis/entry?uuid=' + encodeURIComponent(aegisUuid));
            const data = await resp.json();
            if (!resp.ok) {
                showToast(data.error || 'Failed to load entry details', 'error');
                return;
            }
            document.getElementById('info-modal-title').textContent = 'Aegis Entry Details';
            document.getElementById('info-body').innerHTML = renderAegisInfoBody(data);
            document.getElementById('info-modal').classList.add('open');
        }

        function closeInfo() {
            document.getElementById('info-modal').classList.remove('open');
        }

        let conflictModalResolver = null;

        function renderConflictBody(keepassTitle, linked) {
            const sub = [linked.issuer, linked.name].filter(Boolean).join(' / ');
            return '<p>This KeePass entry is already linked to another Aegis entry.</p>'
                + '<p><strong>KeePass:</strong> ' + escHtml(keepassTitle || '') + '</p>'
                + '<div class="conflict-linked">'
                + '<strong>Linked Aegis entry</strong>'
                + escHtml(linked.display || linked.linked_aegis_display || '')
                + (sub ? '<div class="meta">' + escHtml(sub) + '</div>' : '')
                + '<div class="meta">UUID: ' + escHtml(linked.uuid || linked.linked_aegis_uuid || '') + '</div>'
                + '</div>'
                + '<p>Reassign this KeePass entry to the current Aegis entry?</p>';
        }

        function showConflictModal(keepassTitle, linked) {
            return new Promise((resolve) => {
                conflictModalResolver = resolve;
                document.getElementById('conflict-body').innerHTML = renderConflictBody(keepassTitle, linked);
                document.getElementById('conflict-modal').classList.add('open');
            });
        }

        function closeConflictModal(confirmed) {
            document.getElementById('conflict-modal').classList.remove('open');
            if (conflictModalResolver) {
                conflictModalResolver(confirmed);
                conflictModalResolver = null;
            }
        }

        document.getElementById('conflict-cancel-btn').addEventListener('click', () => closeConflictModal(false));
        document.getElementById('conflict-confirm-btn').addEventListener('click', () => closeConflictModal(true));
        document.getElementById('conflict-modal').addEventListener('click', (e) => {
            if (e.target.id === 'conflict-modal') closeConflictModal(false);
        });

        function renderSearchResults(results, highlightUuid) {
            const container = document.getElementById('search-results');
            if (!results.length) {
                container.innerHTML = '<p class="meta">No results found.</p>';
                return;
            }

            container.innerHTML = results.map(r => {
                const linked = r.linked_aegis_uuid
                    ? '<span class="otp-badge">Linked</span>' : '';
                const otp = r.has_otp ? '<span class="otp-badge">OTP</span>' : '';
                const sub = [r.username, r.url].filter(Boolean).join(' · ');
                let cls = r.linked_aegis_uuid ? ' linked' : '';
                if (highlightUuid && r.uuid === highlightUuid) cls += ' suggested';
                return '<div class="search-result' + cls + '" data-uuid="' + r.uuid + '">'
                    + '<div class="info"><div class="title">' + escHtml(r.title) + ' ' + otp + ' ' + linked + '</div>'
                    + (sub ? '<div class="sub">' + escHtml(sub) + '</div>' : '')
                    + '</div>'
                    + '<div class="result-actions">'
                    + '<button type="button" class="info-kp-btn" data-uuid="' + r.uuid + '" title="Entry details" aria-label="Entry details">ℹ️</button>'
                    + '<button class="btn btn-primary btn-sm select-kp-btn" data-uuid="' + r.uuid + '"'
                    + ' data-title="' + escAttr(r.title) + '"'
                    + ' data-linked-uuid="' + escAttr(r.linked_aegis_uuid || '') + '"'
                    + ' data-linked-display="' + escAttr(r.linked_aegis_display || '') + '"'
                    + ' data-linked-issuer="' + escAttr(r.linked_aegis_issuer || '') + '"'
                    + ' data-linked-name="' + escAttr(r.linked_aegis_name || '') + '">Select</button>'
                    + '</div>'
                    + '</div>';
            }).join('');
        }

        function renderSearchPagination() {
            const el = document.getElementById('search-pagination');
            if (!searchTotal) {
                el.innerHTML = '';
                return;
            }

            const start = searchPage * SEARCH_PAGE_SIZE + 1;
            const end = Math.min((searchPage + 1) * SEARCH_PAGE_SIZE, searchTotal);
            const totalPages = Math.ceil(searchTotal / SEARCH_PAGE_SIZE);
            const canPrev = searchPage > 0;
            const canNext = searchPage < totalPages - 1;

            el.innerHTML = '<button type="button" class="btn btn-secondary btn-sm" id="search-prev"'
                + (canPrev ? '' : ' disabled') + '>Previous</button>'
                + '<span>' + start + '–' + end + ' of ' + searchTotal + '</span>'
                + '<button type="button" class="btn btn-secondary btn-sm" id="search-next"'
                + (canNext ? '' : ' disabled') + '>Next</button>';
        }

        async function searchKeepass(q, highlightUuid, page) {
            if (q !== undefined) keepassSearchQuery = q;
            if (page !== undefined) searchPage = page;

            const params = new URLSearchParams({
                q: keepassSearchQuery,
                limit: SEARCH_PAGE_SIZE,
                offset: searchPage * SEARCH_PAGE_SIZE,
            });
            if (pickerAegisUuid) params.set('exclude_aegis', pickerAegisUuid);
            const resp = await fetch('/api/keepass/search?' + params);
            const data = await resp.json();
            searchTotal = data.total || 0;
            renderSearchResults(data.results, highlightUuid);
            renderSearchPagination();
            document.getElementById('search-results').scrollTop = 0;
        }

        document.getElementById('keepass-search').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => searchKeepass(e.target.value, undefined, 0), 200);
        });

        document.getElementById('search-pagination').addEventListener('click', (e) => {
            if (e.target.id === 'search-prev' && searchPage > 0) {
                searchKeepass(undefined, undefined, searchPage - 1);
            } else if (e.target.id === 'search-next') {
                const totalPages = Math.ceil(searchTotal / SEARCH_PAGE_SIZE);
                if (searchPage < totalPages - 1) {
                    searchKeepass(undefined, undefined, searchPage + 1);
                }
            }
        });

        document.getElementById('search-results').addEventListener('click', (e) => {
            const infoBtn = e.target.closest('.info-kp-btn');
            if (infoBtn) {
                showKeepassInfo(infoBtn.dataset.uuid);
                return;
            }
            const btn = e.target.closest('.select-kp-btn');
            if (btn) {
                const linked = btn.dataset.linkedUuid ? {
                    uuid: btn.dataset.linkedUuid,
                    display: btn.dataset.linkedDisplay,
                    issuer: btn.dataset.linkedIssuer,
                    name: btn.dataset.linkedName,
                } : null;
                selectKeepass(btn.dataset.uuid, btn.dataset.title, linked);
            }
        });

        function conflictInfoFromApi(result) {
            return {
                uuid: result.linked_aegis_uuid,
                display: result.linked_aegis_display,
                issuer: result.linked_aegis_issuer,
                name: result.linked_aegis_name,
            };
        }

        async function suggestMatch(confirmMatch) {
            if (!pickerAegisUuid) return;

            const btn = document.getElementById('suggest-btn');
            btn.disabled = true;
            btn.textContent = 'Suggesting...';

            try {
                const resp = await fetch('/api/keepass/suggest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        aegis_uuid: pickerAegisUuid,
                        confirm: confirmMatch || false,
                    }),
                });
                const result = await resp.json();

                if (!resp.ok) {
                    if (result.error === 'conflict' && result.suggestion) {
                        const ok = await showConflictModal(
                            result.suggestion.keepass_title,
                            conflictInfoFromApi(result),
                        );
                        if (ok) await suggestMatch(true);
                        return;
                    }
                    showToast(result.error || 'No suggestion found', 'error');
                    return;
                }

                const s = result.suggestion;
                const pct = Math.round(s.confidence * 100);
                showToast('Suggested: ' + s.keepass_title + ' (' + pct + '%)', 'success');
                closePicker();
                loadEntries();
            } finally {
                btn.disabled = false;
                btn.textContent = 'Suggest';
            }
        }

        document.getElementById('suggest-btn').addEventListener('click', () => suggestMatch(false));

        async function selectKeepass(keepassUuid, keepassTitle, linkedInfo) {
            if (!pickerAegisUuid) return;

            let confirmMatch = false;
            if (linkedInfo && linkedInfo.uuid) {
                const ok = await showConflictModal(keepassTitle, linkedInfo);
                if (!ok) return;
                confirmMatch = true;
            }

            const resp = await fetch('/api/match', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    aegis_uuid: pickerAegisUuid,
                    keepass_uuid: keepassUuid,
                    confirm: confirmMatch,
                }),
            });

            const result = await resp.json();
            if (!resp.ok) {
                if (result.error === 'conflict') {
                    const ok = await showConflictModal(keepassTitle, conflictInfoFromApi(result));
                    if (!ok) return;
                    const retry = await fetch('/api/match', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            aegis_uuid: pickerAegisUuid,
                            keepass_uuid: keepassUuid,
                            confirm: true,
                        }),
                    });
                    const retryResult = await retry.json();
                    if (retry.ok) {
                        closePicker();
                        loadEntries();
                        return;
                    }
                    showToast(retryResult.error || 'Failed to match', 'error');
                } else {
                    showToast(result.error || 'Failed to match', 'error');
                }
                return;
            }

            closePicker();
            loadEntries();
        }

        async function clearMatch(aegisUuid) {
            const resp = await fetch('/api/match', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ aegis_uuid: aegisUuid }),
            });
            const result = await resp.json();
            if (resp.ok) {
                loadEntries();
            } else {
                showToast(result.error || 'Failed to clear match', 'error');
            }
        }

        document.getElementById('save-btn').addEventListener('click', async () => {
            if (!confirm('Apply imported OTP secrets and save merged KeePass XML to a new file?')) return;

            const resp = await fetch('/api/save', { method: 'POST' });
            const result = await resp.json();
            if (result.success) {
                const label = result.output_name || result.output_path;
                showToast('Saved: ' + label + ' (' + result.updated_count + ' updated, ' + result.cleaned_count + ' cleaned)', 'success');
                loadEntries();
            } else {
                showToast(result.error || 'Save failed', 'error');
            }
        });

        document.getElementById('close-btn').addEventListener('click', async () => {
            if (!confirm('Stop the server and close the app?')) return;
            intentionalShutdown = true;
            try {
                await fetch('/api/shutdown', { method: 'POST' });
            } catch (e) {}
            showServerStopped();
        });

        window.addEventListener('pagehide', () => {
            if (intentionalShutdown) return;
            const nav = performance.getEntriesByType('navigation')[0];
            if (nav && nav.type === 'reload') return;
            requestServerShutdown();
        });

        document.getElementById('picker-modal').addEventListener('click', (e) => {
            if (e.target.id === 'picker-modal') closePicker();
        });

        document.getElementById('entries-body').addEventListener('click', (e) => {
            const aegisInfoBtn = e.target.closest('.info-aegis-btn');
            if (aegisInfoBtn) {
                showAegisInfo(aegisInfoBtn.dataset.uuid);
                return;
            }
            const infoBtn = e.target.closest('.info-kp-btn');
            if (infoBtn) {
                showKeepassInfo(infoBtn.dataset.uuid);
                return;
            }
            const pickerBtn = e.target.closest('.picker-btn');
            if (pickerBtn) {
                openPicker(pickerBtn.dataset.uuid, pickerBtn.dataset.display);
                return;
            }
            const clearBtn = e.target.closest('.clear-btn');
            if (clearBtn) {
                clearMatch(clearBtn.dataset.uuid);
            }
        });

        document.getElementById('info-close-btn').addEventListener('click', closeInfo);
        document.getElementById('info-modal').addEventListener('click', (e) => {
            if (e.target.id === 'info-modal') closeInfo();
        });

        loadEntries();
    </script>
</body>
</html>
'''


_MANUAL_PATH_CHOICE = '[Enter path manually]'


def _is_interactive_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _files_in_cwd(extension: str) -> List[str]:
    ext = extension if extension.startswith('.') else f'.{extension}'
    ext = ext.lower()
    return sorted(
        path.name
        for path in Path('.').iterdir()
        if path.is_file() and path.suffix.lower() == ext
    )


def _arrow_select(title: str, choices: List[str]) -> Optional[str]:
    """Select one item with arrow keys. Returns None if cancelled."""
    if not choices:
        return None

    def _run(stdscr) -> Optional[str]:
        curses.curs_set(0)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)

        index = 0
        offset = 0

        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            list_height = max(height - 4, 1)

            stdscr.addstr(0, 0, title[: max(width - 1, 0)])
            stdscr.addstr(1, 0, 'Use ↑/↓ to move, Enter to select, Esc to cancel'[: max(width - 1, 0)])

            visible = choices[offset: offset + list_height]
            for row, choice in enumerate(visible):
                item_index = offset + row
                label = f'> {choice}' if item_index == index else f'  {choice}'
                if item_index == index and curses.has_colors():
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(row + 3, 0, label[: max(width - 1, 0)])
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(row + 3, 0, label[: max(width - 1, 0)])

            stdscr.refresh()
            key = stdscr.getch()

            if key in (curses.KEY_UP, ord('k')):
                if index > 0:
                    index -= 1
                    if index < offset:
                        offset = index
            elif key in (curses.KEY_DOWN, ord('j')):
                if index < len(choices) - 1:
                    index += 1
                    if index >= offset + list_height:
                        offset = index - list_height + 1
            elif key in (curses.KEY_ENTER, 10, 13):
                return choices[index]
            elif key == 27:
                return None

    try:
        return curses.wrapper(_run)
    except curses.error:
        return None


def _prompt_text(label: str) -> str:
    while True:
        value = input(f'{label}: ').strip()
        if value:
            return value
        print('Please enter a value.')


def _prompt_file_path(label: str, extension: str) -> str:
    ext = extension if extension.startswith('.') else f'.{extension}'
    files = _files_in_cwd(ext)

    if _is_interactive_tty() and files:
        choices = files + [_MANUAL_PATH_CHOICE]
        selected = _arrow_select(f'Select {label} ({ext} files in current folder):', choices)
        if selected is None:
            print('Cancelled.')
            sys.exit(1)
        if selected != _MANUAL_PATH_CHOICE:
            return selected

    while True:
        value = _prompt_text(f'{label} path ({ext})')
        if Path(value).suffix.lower() == ext.lower():
            return value
        print(f'Expected a file with the {ext} extension.')


def _read_password_file(path: str) -> str:
    if not os.path.exists(path):
        print(f'Error: Password file not found: {path}')
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def _prompt_aegis_password() -> str:
    enter_choice = 'Enter password'
    file_choice = 'Read password from file'

    if _is_interactive_tty():
        selected = _arrow_select('Aegis backup password:', [enter_choice, file_choice])
        if selected is None:
            print('Cancelled.')
            sys.exit(1)
        if selected == enter_choice:
            while True:
                password = getpass.getpass('Enter Aegis backup password: ')
                if password:
                    return password
                print('Password cannot be empty.')
        password_path = _prompt_file_path('Aegis password', '.txt')
        return _read_password_file(password_path)

    password = getpass.getpass('Enter Aegis backup password: ')
    if not password:
        print('Error: Password cannot be empty.')
        sys.exit(1)
    return password


def _resolve_cli_args(args: argparse.Namespace) -> argparse.Namespace:
    if not args.aegis:
        args.aegis = _prompt_file_path('Aegis backup', '.json')
    if not args.keepass:
        args.keepass = _prompt_file_path('KeePass XML', '.xml')
    return args


def open_browser(url: str) -> None:
    """Auto-open the browser to the specified URL."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == "win32":
            subprocess.Popen(["cmd", "/c", "start", "", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            browser = os.environ.get("BROWSER")
            if browser:
                subprocess.Popen(f"{browser} {shlex.quote(url)}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as err:
        print(f"[editor] Failed to open browser: {err}", file=sys.stderr)


def main():
    if not CRYPTO_AVAILABLE:
        print("ERROR: The 'cryptography' library is required to decrypt Aegis backups.")
        print("Please install it with: pip install cryptography")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description='Import Aegis OTP secrets into KeePass — web UI for matching, applying, and merging',
    )
    parser.add_argument('--aegis', help='Path to encrypted Aegis backup JSON')
    parser.add_argument('--keepass', help='Path to KeePass XML')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind (default: 5000)')
    parser.add_argument('--password-file', type=str, help='Path to file containing Aegis backup password')
    parser.add_argument('--output', type=str, help='Merged output XML path (default: <keepass-stem>-merged.xml)')
    args = parser.parse_args()
    args = _resolve_cli_args(args)

    if not os.path.exists(args.aegis):
        print(f"Error: Aegis file not found: {args.aegis}")
        sys.exit(1)
    if not os.path.exists(args.keepass):
        print(f"Error: KeePass file not found: {args.keepass}")
        sys.exit(1)

    password = None
    if args.password_file:
        password = _read_password_file(args.password_file)

    if not AegisDecryptor.is_encrypted(args.aegis):
        print("ERROR: Only encrypted Aegis backup files are supported.")
        sys.exit(1)

    if password is None:
        password = _prompt_aegis_password()

    print(f"Loading Aegis entries from: {args.aegis}")
    app_data['aegis_entries'] = AegisParser.parse(args.aegis, password=password)
    print(f"  Found {len(app_data['aegis_entries'])} entries")

    print(f"Loading KeePass entries from: {args.keepass}")
    app_data['keepass_entries'], app_data['tree'], recycle_bin_count = KeePassParser.parse(args.keepass)
    history_count = sum(1 for e in app_data['keepass_entries'] if e.in_history)
    matchable_count = len(_matchable_keepass_entries())
    print(f"  Found {len(app_data['keepass_entries'])} entries")
    if history_count:
        print(f"  History snapshots: {history_count} (excluded from matching)")
    if recycle_bin_count:
        print(f"  Recycle bin: {recycle_bin_count} entries (excluded from matching)")
    print(f"  Matchable: {matchable_count} entries")

    print("Running matcher...")
    matcher = EntryMatcher()
    matches, unmatched = matcher.find_matches(
        app_data['aegis_entries'],
        _matchable_keepass_entries(),
    )
    _init_match_assignments(matches, unmatched)

    app_data['keepass_path'] = args.keepass
    if args.output:
        app_data['output_path'] = args.output
    else:
        kp_path_obj = Path(args.keepass)
        app_data['output_path'] = str(kp_path_obj.with_name(f"{kp_path_obj.stem}-merged{kp_path_obj.suffix}"))

    matched_count = sum(1 for a in app_data['match_assignments'].values() if a.get('keepass_uuid'))
    print(f"\n  Auto-matched: {matched_count}")
    print(f"  Unmatched: {len(app_data['aegis_entries']) - matched_count}")

    port = args.port
    max_port = port + 50
    success = False

    for current_port in range(port, max_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((args.host, current_port))
            port = current_port
            success = True
            break
        except OSError:
            print(f"Port {current_port} is already in use, trying next port...")
            continue

    if not success:
        print(f"Error: No available port found in the range {args.port} to {max_port - 1}.", file=sys.stderr)
        sys.exit(1)

    url_host = '127.0.0.1' if args.host == '0.0.0.0' else args.host
    url = f"http://{url_host}:{port}"

    print(f"\nStarting web server at {url}")
    print("Press Ctrl+C or Close in the browser to stop")

    def trigger_browser():
        time.sleep(1)
        open_browser(url)

    threading.Thread(target=trigger_browser, daemon=True).start()

    app.run(host=args.host, port=port, debug=False)


if __name__ == '__main__':
    main()
