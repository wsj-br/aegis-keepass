#!/usr/bin/env python3
"""
Aegis-KeePass OTP Sync Web Interface

Interactive web UI for matching Aegis OTP entries with KeePass entries.
Useful for manually reviewing and approving matches.

Usage:
    python3 aegis_keepass_web.py --aegis aegis-backup.json --keepass keepass.xml
    python3 aegis_keepass_web.py --aegis aegis-backup.json --keepass keepass.xml --password-file pass.txt

Then open http://localhost:5000 in your browser.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
import re
from typing import List, Dict, Optional

from flask import Flask, render_template_string, request, jsonify

# Import from main sync script
from aegis_keepass_sync import (
    AegisParser, KeePassParser, EntryMatcher,
    KeePassUpdater, create_backup, AegisEntry, KeePassEntry,
    AegisDecryptor, CRYPTO_AVAILABLE
)

app = Flask(__name__)

# Global storage for loaded data
app_data = {
    'aegis_entries': [],
    'keepass_entries': [],
    'tree': None,
    'matches': [],
    'unmatched': [],
    'manual_matches': {},  # aegis_uuid -> keepass_uuid
    'keepass_path': None
}


def normalize(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ''
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


@app.route('/')
def index():
    """Main dashboard showing matching overview."""
    total = len(app_data['aegis_entries'])
    matched = len(app_data['matches'])
    unmatched = len(app_data['unmatched'])
    manual = len(app_data['manual_matches'])
    
    return render_template_string(INDEX_TEMPLATE,
        total=total,
        matched=matched,
        unmatched=unmatched,
        manual=manual,
        match_rate=(matched/total*100) if total > 0 else 0
    )


@app.route('/unmatched')
def unmatched():
    """Show unmatched Aegis entries for manual matching."""
    entries = []
    for entry in app_data['unmatched']:
        # Find potential matches in KeePass
        candidates = []
        for kp_entry in app_data['keepass_entries']:
            if kp_entry.uuid in app_data['manual_matches'].values():
                continue  # Skip already matched
            
            scores = []
            sim = similarity(entry.full_identifier, kp_entry.title)
            if sim > 0.3:
                scores.append(('full', sim))
            sim = similarity(entry.issuer, kp_entry.title)
            if sim > 0.3:
                scores.append(('issuer', sim))
            sim = similarity(entry.name, kp_entry.title)
            if sim > 0.3:
                scores.append(('name', sim))
            
            if scores:
                max_score = max(s[1] for s in scores)
                candidates.append({
                    'uuid': kp_entry.uuid,
                    'title': kp_entry.title,
                    'score': max_score,
                    'has_otp': kp_entry.has_otp()
                })
        
        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        entries.append({
            'uuid': entry.uuid,
            'display': entry.display_name,
            'issuer': entry.issuer,
            'name': entry.name,
            'secret': entry.secret[:10] + '...' if len(entry.secret) > 10 else entry.secret,
            'candidates': candidates[:5]  # Top 5 candidates
        })
    
    return render_template_string(UNMATCHED_TEMPLATE, entries=entries)


@app.route('/matched')
def matched():
    """Show automatically matched entries for review."""
    matches = []
    for match in app_data['matches']:
        matches.append({
            'aegis_uuid': match['aegis_uuid'],
            'aegis_display': match['aegis_display'],
            'keepass_title': match['keepass_title'],
            'keepass_uuid': match['keepass_uuid'],
            'confidence': match['confidence'],
            'reason': match['reason'],
            'has_existing_otp': match['has_existing_otp']
        })
    
    return render_template_string(MATCHED_TEMPLATE, matches=matches)


@app.route('/api/match', methods=['POST'])
def api_match():
    """API endpoint to create a manual match."""
    data = request.json
    aegis_uuid = data.get('aegis_uuid')
    keepass_uuid = data.get('keepass_uuid')
    
    if not aegis_uuid or not keepass_uuid:
        return jsonify({'error': 'Missing UUIDs'}), 400
    
    app_data['manual_matches'][aegis_uuid] = keepass_uuid
    
    return jsonify({'success': True, 'matches_count': len(app_data['manual_matches'])})


@app.route('/api/unmatch', methods=['POST'])
def api_unmatch():
    """API endpoint to remove a manual match."""
    data = request.json
    aegis_uuid = data.get('aegis_uuid')
    
    if aegis_uuid in app_data['manual_matches']:
        del app_data['manual_matches'][aegis_uuid]
    
    return jsonify({'success': True})


@app.route('/apply', methods=['POST'])
def apply():
    """Apply all matches to the KeePass XML."""
    if not app_data['keepass_path'] or not app_data['tree']:
        return jsonify({'error': 'No KeePass file loaded'}), 400
    
    # Create backup
    backup_path = create_backup(app_data['keepass_path'])
    
    # Build list of all matches (automatic + manual)
    all_matches = []
    
    # Add automatic matches
    for match_data in app_data['matches']:
        aegis_entry = next((e for e in app_data['aegis_entries'] 
                           if e.uuid == match_data['aegis_uuid']), None)
        kp_entry = next((e for e in app_data['keepass_entries'] 
                        if e.uuid == match_data['keepass_uuid']), None)
        if aegis_entry and kp_entry:
            from aegis_keepass_sync import MatchResult
            all_matches.append(MatchResult(
                aegis_entry=aegis_entry,
                keepass_entry=kp_entry,
                confidence=match_data['confidence'],
                match_reason=match_data['reason']
            ))
    
    # Add manual matches
    for aegis_uuid, keepass_uuid in app_data['manual_matches'].items():
        aegis_entry = next((e for e in app_data['aegis_entries'] 
                           if e.uuid == aegis_uuid), None)
        kp_entry = next((e for e in app_data['keepass_entries'] 
                        if e.uuid == keepass_uuid), None)
        if aegis_entry and kp_entry:
            from aegis_keepass_sync import MatchResult
            all_matches.append(MatchResult(
                aegis_entry=aegis_entry,
                keepass_entry=kp_entry,
                confidence=1.0,
                match_reason='Manual match'
            ))
    
    # Apply updates
    updater = KeePassUpdater(app_data['tree'])
    updated_count = 0
    
    for match in all_matches:
        changes = updater.update_entry(match, dry_run=False)
        if changes['fields_added'] or changes['fields_updated']:
            updated_count += 1
    
    # Save
    updater.save(app_data['keepass_path'])
    
    return jsonify({
        'success': True,
        'backup_path': backup_path,
        'updated_entries': updated_count,
        'total_matches': len(all_matches)
    })


# HTML Templates
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Aegis-KeePass Sync</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
        .stat { background: #f5f5f5; padding: 20px; border-radius: 8px; text-align: center; }
        .stat h3 { margin: 0; font-size: 2em; color: #333; }
        .stat p { margin: 5px 0 0; color: #666; }
        .actions { display: flex; gap: 10px; margin: 30px 0; }
        .btn { padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 500; }
        .btn-primary { background: #0066cc; color: white; }
        .btn-secondary { background: #f0f0f0; color: #333; }
        .progress { background: #e0e0e0; height: 20px; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .progress-bar { background: #00aa44; height: 100%; }
    </style>
</head>
<body>
    <h1>Aegis-KeePass OTP Sync</h1>
    
    <div class="stats">
        <div class="stat">
            <h3>{{ total }}</h3>
            <p>Total Aegis Entries</p>
        </div>
        <div class="stat">
            <h3>{{ matched }}</h3>
            <p>Auto-Matched</p>
        </div>
        <div class="stat">
            <h3>{{ unmatched }}</h3>
            <p>Unmatched</p>
        </div>
        <div class="stat">
            <h3>{{ manual }}</h3>
            <p>Manual Matches</p>
        </div>
    </div>
    
    <div class="progress">
        <div class="progress-bar" style="width: {{ match_rate }}%"></div>
    </div>
    <p>Match rate: {{ "%.1f"|format(match_rate) }}%</p>
    
    <div class="actions">
        <a href="/unmatched" class="btn btn-primary">Review Unmatched Entries</a>
        <a href="/matched" class="btn btn-secondary">Review Auto-Matches</a>
    </div>
    
    {% if manual > 0 or matched > 0 %}
    <div style="margin-top: 30px; padding: 20px; background: #fff8e1; border-radius: 8px;">
        <h3>Ready to Apply</h3>
        <p>{{ matched }} automatic + {{ manual }} manual matches ready to sync to KeePass.</p>
        <button onclick="applyChanges()" class="btn btn-primary" style="border: none; cursor: pointer;">
            Apply Changes to KeePass
        </button>
    </div>
    {% endif %}
    
    <script>
        async function applyChanges() {
            if (!confirm("This will modify your KeePass XML file. A backup will be created. Continue?")) {
                return;
            }
            
            const response = await fetch('/apply', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                alert(`Success! Updated ${result.updated_entries} entries.\\nBackup: ${result.backup_path}`);
            } else {
                alert('Error: ' + result.error);
            }
        }
    </script>
</body>
</html>
'''

UNMATCHED_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Unmatched Entries - Aegis-KeePass Sync</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 1000px; margin: 40px auto; padding: 0 20px; }
        .entry { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 15px 0; }
        .entry h3 { margin: 0 0 10px; }
        .meta { color: #666; font-size: 0.9em; margin: 5px 0; }
        .candidates { margin-top: 15px; }
        .candidate { 
            display: flex; align-items: center; gap: 10px; 
            padding: 8px; margin: 5px 0; background: #f5f5f5; border-radius: 4px;
        }
        .candidate:hover { background: #e8f0fe; }
        .score { 
            background: #0066cc; color: white; padding: 2px 8px; 
            border-radius: 12px; font-size: 0.8em; 
        }
        .btn { 
            padding: 6px 12px; border: none; border-radius: 4px; 
            cursor: pointer; font-size: 0.9em;
        }
        .btn-match { background: #00aa44; color: white; }
        .btn-skip { background: #ccc; color: #333; }
        .otp-badge { background: #ff9800; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; }
        .back { margin-bottom: 20px; }
        .back a { color: #0066cc; text-decoration: none; }
        .matched { background: #d4edda !important; }
    </style>
</head>
<body>
    <div class="back"><a href="/">← Back to Dashboard</a></div>
    <h1>Unmatched Aegis Entries</h1>
    <p>Select a KeePass entry to match with each Aegis OTP entry.</p>
    
    {% for entry in entries %}
    <div class="entry" id="entry-{{ entry.uuid }}">
        <h3>{{ entry.display }}</h3>
        <div class="meta">Issuer: {{ entry.issuer or 'N/A' }} | Name: {{ entry.name or 'N/A' }}</div>
        <div class="meta">Secret: {{ entry.secret }}</div>
        
        <div class="candidates">
            <h4>Suggested KeePass Matches:</h4>
            {% if entry.candidates %}
                {% for candidate in entry.candidates %}
                <div class="candidate" id="candidate-{{ entry.uuid }}-{{ candidate.uuid }}">
                    <span class="score">{{ "%.0f"|format(candidate.score * 100) }}%</span>
                    <span style="flex: 1;">{{ candidate.title }}</span>
                    {% if candidate.has_otp %}
                    <span class="otp-badge">Has OTP</span>
                    {% endif %}
                    <button class="btn btn-match" onclick="matchEntry('{{ entry.uuid }}', '{{ candidate.uuid }}')">
                        Match
                    </button>
                </div>
                {% endfor %}
            {% else %}
                <p style="color: #666;">No good candidates found. Try manually matching in KeePass.</p>
            {% endif %}
        </div>
        
        <div style="margin-top: 15px;">
            <button class="btn btn-skip" onclick="skipEntry('{{ entry.uuid }}')">Skip This Entry</button>
        </div>
    </div>
    {% endfor %}
    
    <script>
        async function matchEntry(aegisUuid, keepassUuid) {
            const response = await fetch('/api/match', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ aegis_uuid: aegisUuid, keepass_uuid: keepassUuid })
            });
            
            const result = await response.json();
            if (result.success) {
                document.getElementById('entry-' + aegisUuid).classList.add('matched');
                document.querySelectorAll('[id^="candidate-' + aegisUuid + '"]').forEach(el => {
                    el.style.opacity = '0.5';
                });
            }
        }
        
        function skipEntry(uuid) {
            document.getElementById('entry-' + uuid).style.display = 'none';
        }
    </script>
</body>
</html>
'''

MATCHED_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Auto-Matched Entries - Aegis-KeePass Sync</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 1000px; margin: 40px auto; padding: 0 20px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f5f5f5; font-weight: 600; }
        .confidence { 
            background: #0066cc; color: white; padding: 2px 8px; 
            border-radius: 12px; font-size: 0.8em; 
        }
        .confidence-low { background: #ff9800; }
        .back { margin-bottom: 20px; }
        .back a { color: #0066cc; text-decoration: none; }
        .otp-exists { color: #ff9800; font-size: 0.85em; }
    </style>
</head>
<body>
    <div class="back"><a href="/">← Back to Dashboard</a></div>
    <h1>Automatically Matched Entries</h1>
    <p>Review the automatic matches before applying changes.</p>
    
    <table>
        <thead>
            <tr>
                <th>Aegis Entry</th>
                <th>KeePass Entry</th>
                <th>Confidence</th>
                <th>Reason</th>
            </tr>
        </thead>
        <tbody>
            {% for match in matches %}
            <tr>
                <td>
                    {{ match.aegis_display }}
                </td>
                <td>
                    {{ match.keepass_title }}
                    {% if match.has_existing_otp %}
                    <br><span class="otp-exists">⚠️ Has existing OTP - will be updated</span>
                    {% endif %}
                </td>
                <td>
                    <span class="confidence {{ 'confidence-low' if match.confidence < 0.8 else '' }}">
                        {{ "%.0f"|format(match.confidence * 100) }}%
                    </span>
                </td>
                <td>{{ match.reason }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
'''


def main():
    if not CRYPTO_AVAILABLE:
        print("ERROR: The 'cryptography' library is required to decrypt Aegis backups.")
        print("Please install it with: pip install cryptography")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Web UI for Aegis-KeePass OTP Sync')
    parser.add_argument('--aegis', required=True, help='Path to encrypted Aegis backup JSON')
    parser.add_argument('--keepass', required=True, help='Path to KeePass XML')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind (default: 5000)')
    parser.add_argument('--password-file', type=str, help='Path to file containing Aegis backup password')
    args = parser.parse_args()

    # Verify files
    if not os.path.exists(args.aegis):
        print(f"Error: Aegis file not found: {args.aegis}")
        sys.exit(1)
    if not os.path.exists(args.keepass):
        print(f"Error: KeePass file not found: {args.keepass}")
        sys.exit(1)

    # Read password from file if provided
    password = None
    if args.password_file:
        if not os.path.exists(args.password_file):
            print(f"Error: Password file not found: {args.password_file}")
            sys.exit(1)
        with open(args.password_file, 'r', encoding='utf-8') as f:
            password = f.read().strip()

    # Check if file is encrypted
    is_encrypted = AegisDecryptor.is_encrypted(args.aegis)
    if not is_encrypted:
        print("ERROR: Only encrypted Aegis backup files are supported.")
        sys.exit(1)

    # Load data
    print(f"Loading Aegis entries from: {args.aegis}")
    app_data['aegis_entries'] = AegisParser.parse(args.aegis, password=password)
    print(f"  Found {len(app_data['aegis_entries'])} entries")
    
    print(f"Loading KeePass entries from: {args.keepass}")
    app_data['keepass_entries'], app_data['tree'] = KeePassParser.parse(args.keepass)
    print(f"  Found {len(app_data['keepass_entries'])} entries")
    
    # Run matching
    print("Running matcher...")
    matcher = EntryMatcher()
    matches, unmatched = matcher.find_matches(app_data['aegis_entries'], app_data['keepass_entries'])
    
    # Store matches in serializable format
    app_data['matches'] = [
        {
            'aegis_uuid': m.aegis_entry.uuid,
            'aegis_display': m.aegis_entry.display_name,
            'keepass_uuid': m.keepass_entry.uuid,
            'keepass_title': m.keepass_entry.title,
            'confidence': m.confidence,
            'reason': m.match_reason,
            'has_existing_otp': m.keepass_entry.has_otp()
        }
        for m in matches
    ]
    app_data['unmatched'] = unmatched
    app_data['keepass_path'] = args.keepass
    
    print(f"\n  Auto-matched: {len(matches)}")
    print(f"  Unmatched: {len(unmatched)}")
    
    print(f"\nStarting web server at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
