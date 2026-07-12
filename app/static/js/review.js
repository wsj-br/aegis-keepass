let currentStatus = 'all';
let aegisFilter = '';
let pickerAegisUuid = null;
let searchTimeout = null;
let searchPage = 0;
let searchTotal = 0;
let keepassSearchQuery = '';
const SEARCH_PAGE_SIZE = 25;
let conflictModalResolver = null;

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
    if (resp.status === 401) {
        window.location.href = '/';
        return;
    }
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
    document.getElementById('search-results').innerHTML = '<p class="meta">Loading…</p>';
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
        + detailField('Username', data.username)
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
        + detailField('Issuer', data.issuer)
        + detailField('Name', data.name)
        + detailField('Algorithm', data.algo)
        + detailField('Digits', data.digits)
        + detailField('Period', data.period)
        + detailField('Type', data.entry_type)
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
        const linked = r.linked_aegis_uuid ? '<span class="otp-badge">Linked</span>' : '';
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
    btn.textContent = 'Suggesting…';

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
            if (retry.ok) {
                closePicker();
                loadEntries();
                return;
            }
            const retryResult = await retry.json();
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

function showCompleteView(summary) {
    document.getElementById('step-upload').className = 'step done';
    document.getElementById('step-review').className = 'step done';
    document.getElementById('step-download').className = 'step active';

    document.getElementById('review-workspace').hidden = true;

    document.getElementById('complete-total').textContent = summary.total;
    document.getElementById('complete-otp').textContent = summary.otp;
    document.getElementById('complete-updated').textContent = summary.updated;
    document.getElementById('complete-cleaned').textContent = summary.cleaned;
    document.getElementById('complete-section').hidden = false;
}

document.getElementById('save-btn').addEventListener('click', async () => {
    if (!confirm('Apply imported OTP secrets and download merged KeePass database?')) return;

    const btn = document.getElementById('save-btn');
    btn.disabled = true;

    try {
        const resp = await fetch('/api/save', { method: 'POST' });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            showToast(err.error || 'Save failed', 'error');
            return;
        }

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'keepass-merged.kdbx';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        const updated = resp.headers.get('X-Updated-Count') || '0';
        const cleaned = resp.headers.get('X-Cleaned-Count') || '0';
        const total = resp.headers.get('X-Total-Entries') || '0';
        const otp = resp.headers.get('X-Otp-Entries') || '0';
        showCompleteView({ total, otp, updated, cleaned });
    } catch (err) {
        showToast('Save failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
    }
});

document.getElementById('end-session-btn').addEventListener('click', async () => {
    if (!confirm('End this session and wipe all data from memory?')) return;

    try {
        await fetch('/api/session/end', { method: 'POST' });
    } catch (e) {}
    window.location.href = '/';
});

document.getElementById('complete-end-session-btn').addEventListener('click', () => {
    window.location.href = '/';
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
