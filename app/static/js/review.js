let currentStatus = 'all';
let aegisFilter = '';
let pickerAegisUuid = null;
let searchTimeout = null;
let searchPage = 0;
let searchTotal = 0;
let keepassSearchQuery = '';
const SEARCH_PAGE_SIZE = 25;
let conflictModalResolver = null;
const dialogStack = [];

function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}

function escAttr(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

function getFocusable(container) {
    if (!container) return [];
    const selector = [
        'a[href]',
        'button:not([disabled])',
        'input:not([disabled]):not([type="hidden"])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        '[tabindex]:not([tabindex="-1"])',
    ].join(', ');
    return Array.from(container.querySelectorAll(selector)).filter((el) => {
        if (el.getAttribute('aria-hidden') === 'true') return false;
        if (el.classList.contains('visually-hidden') && el.tabIndex < 0) return false;
        return true;
    });
}

function openDialog(overlay, initialFocus) {
    if (!overlay || overlay.classList.contains('open')) {
        if (overlay && overlay.classList.contains('open') && initialFocus) {
            initialFocus.focus();
        }
        return;
    }
    dialogStack.push({
        overlay: overlay,
        prevFocus: document.activeElement,
    });
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    const dialog = overlay.querySelector('[role="dialog"]') || overlay;
    requestAnimationFrame(() => {
        const focusables = getFocusable(dialog);
        const target = initialFocus && dialog.contains(initialFocus)
            ? initialFocus
            : focusables[0];
        if (target) target.focus();
    });
}

function closeDialog(overlay) {
    if (!overlay || !overlay.classList.contains('open')) return;
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    const idx = dialogStack.findIndex((entry) => entry.overlay === overlay);
    if (idx < 0) return;
    const entry = dialogStack.splice(idx, 1)[0];
    if (dialogStack.length) {
        const top = dialogStack[dialogStack.length - 1];
        const dialog = top.overlay.querySelector('[role="dialog"]') || top.overlay;
        const focusables = getFocusable(dialog);
        if (focusables.length && !top.overlay.contains(document.activeElement)) {
            focusables[0].focus();
        }
        return;
    }
    if (entry.prevFocus && typeof entry.prevFocus.focus === 'function') {
        entry.prevFocus.focus();
    }
}

function topDialogOverlay() {
    return dialogStack.length ? dialogStack[dialogStack.length - 1].overlay : null;
}

function syncFilterPressed() {
    document.querySelectorAll('.filter-btn').forEach((btn) => {
        btn.setAttribute(
            'aria-pressed',
            btn.classList.contains('active') ? 'true' : 'false',
        );
    });
}

document.addEventListener('keydown', (e) => {
    const overlay = topDialogOverlay();
    if (!overlay) return;
    const dialog = overlay.querySelector('[role="dialog"]') || overlay;

    if (e.key === 'Escape') {
        e.preventDefault();
        if (overlay.id === 'conflict-modal') {
            closeConflictModal(false);
        } else if (overlay.id === 'info-modal') {
            closeInfo();
        } else if (overlay.id === 'picker-modal') {
            closePicker();
        } else if (overlay.id === 'save-modal') {
            if (!saveProgress.busy) closeSaveModal();
        } else if (overlay.id === 'end-session-modal') {
            closeEndSessionModal();
        }
        return;
    }

    if (e.key !== 'Tab') return;
    const focusables = getFocusable(dialog);
    if (!focusables.length) {
        e.preventDefault();
        return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
    } else if (!dialog.contains(document.activeElement)) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
    }
});

const INFO_ICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M12 10v6"></path><path d="M12 7h.01"></path></svg>';

async function loadEntries() {
    const tbody = document.getElementById('entries-body');
    const params = new URLSearchParams({ status: currentStatus, q: aegisFilter });
    let resp;
    try {
        resp = await fetch('/api/aegis-entries?' + params);
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">Could not load entries. Check your connection and try again.</td></tr>';
        showToast('Failed to load entries: ' + err.message, 'error');
        return;
    }
    if (resp.status === 401) {
        window.location.href = '/';
        return;
    }
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        tbody.innerHTML = '<tr><td colspan="5" class="empty">Could not load entries.</td></tr>';
        showToast(err.error || 'Failed to load entries', 'error');
        return;
    }
    const data = await resp.json();

    document.getElementById('stat-total').textContent = data.stats.total;
    document.getElementById('stat-matched').textContent = data.stats.matched;
    document.getElementById('stat-unmatched').textContent = data.stats.unmatched;

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
                + '<button type="button" class="info-kp-btn" data-uuid="' + e.keepass_uuid + '" title="Entry details" aria-label="Entry details">' + INFO_ICON + '</button>'
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
            + '<td class="col-status">' + statusBadge + modBadge + '</td>'
            + '<td class="col-aegis"><div class="aegis-title-row"><strong>' + escHtml(e.display) + '</strong>'
            + '<button type="button" class="info-aegis-btn" data-uuid="' + e.aegis_uuid + '" title="Entry details" aria-label="Entry details">' + INFO_ICON + '</button>'
            + '</div>'
            + '<div class="meta">' + escHtml(e.issuer) + ' / ' + escHtml(e.name) + '</div></td>'
            + '<td class="col-keepass">' + kpCell + '</td>'
            + '<td class="col-match">' + matchInfo + '</td>'
            + '<td class="col-actions actions">' + actions + '</td>'
            + '</tr>';
    }).join('');
}

document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        syncFilterPressed();
        currentStatus = btn.dataset.status;
        loadEntries();
    });
});
syncFilterPressed();

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
    const searchInput = document.getElementById('keepass-search');
    searchInput.value = '';
    document.getElementById('search-results').innerHTML = '<p class="meta">Loading…</p>';
    document.getElementById('search-pagination').innerHTML = '';
    openDialog(document.getElementById('picker-modal'), searchInput);
    searchKeepass('');
}

function closePicker() {
    pickerAegisUuid = null;
    closeDialog(document.getElementById('picker-modal'));
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
    openDialog(
        document.getElementById('info-modal'),
        document.getElementById('info-close-btn'),
    );
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
    openDialog(
        document.getElementById('info-modal'),
        document.getElementById('info-close-btn'),
    );
}

function closeInfo() {
    closeDialog(document.getElementById('info-modal'));
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
        openDialog(
            document.getElementById('conflict-modal'),
            document.getElementById('conflict-cancel-btn'),
        );
    });
}

function closeConflictModal(confirmed) {
    closeDialog(document.getElementById('conflict-modal'));
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
            + '<button type="button" class="info-kp-btn" data-uuid="' + r.uuid + '" title="Entry details" aria-label="Entry details">' + INFO_ICON + '</button>'
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

const AK_DESKTOP = !!window.AK_DESKTOP;
const SAVE_ACTION = AK_DESKTOP ? 'Save merged database' : 'Download merged database';

const SAVE_STEPS = [
    {
        id: 'cleanup',
        label: 'Cleaning stale OTP links',
        detail: 'Removing Aegis markers and OTP fields from unlinked KeePass entries.',
    },
    {
        id: 'apply',
        label: 'Applying OTP secrets',
        detail: 'Writing TimeOtp fields and AegisUUID markers for matched entries.',
    },
    {
        id: 'build',
        label: 'Building merged database',
        detail: 'Encrypting the updated KeePass database in memory.',
    },
    {
        id: 'download',
        label: AK_DESKTOP ? 'Saving database' : 'Preparing download',
        detail: AK_DESKTOP
            ? 'Writing keepass-merged.kdbx and wiping the session.'
            : 'Sending keepass-merged.kdbx to your browser and wiping the session.',
    },
];

class SaveProgress {
    constructor() {
        this.overlay = document.getElementById('save-modal');
        this.title = document.getElementById('save-modal-title');
        this.confirmPanel = document.getElementById('save-confirm-panel');
        this.progressPanel = document.getElementById('save-progress-panel');
        this.detail = document.getElementById('save-progress-detail');
        this.list = document.getElementById('save-progress-steps');
        this.footer = document.getElementById('save-modal-footer');
        this.cancelBtn = document.getElementById('save-cancel-btn');
        this.confirmBtn = document.getElementById('save-confirm-btn');
        this.busy = false;
    }

    openConfirm() {
        this.busy = false;
        this.overlay.classList.remove('busy');
        this.title.textContent = SAVE_ACTION + '?';
        this.confirmPanel.hidden = false;
        this.progressPanel.hidden = true;
        this.progressPanel.setAttribute('aria-busy', 'false');
        this.footer.hidden = false;
        this.cancelBtn.disabled = false;
        this.confirmBtn.disabled = false;
        openDialog(this.overlay, this.confirmBtn);
    }

    startProgress() {
        this.busy = true;
        this.overlay.classList.add('busy');
        this.title.textContent = AK_DESKTOP ? 'Merging and saving' : 'Merging and downloading';
        this.confirmPanel.hidden = true;
        this.progressPanel.hidden = false;
        this.progressPanel.setAttribute('aria-busy', 'true');
        this.footer.hidden = true;
        this.list.innerHTML = '';
        this.detail.textContent = 'Starting…';

        const dialog = this.overlay.querySelector('[role="dialog"]');
        if (dialog) {
            dialog.setAttribute('tabindex', '-1');
            dialog.focus();
        }

        for (const step of SAVE_STEPS) {
            const item = document.createElement('li');
            item.className = 'progress-step pending';
            item.dataset.step = step.id;
            item.innerHTML =
                '<span class="progress-step-icon" aria-hidden="true"></span>' +
                '<span class="progress-step-text">' +
                    '<span class="progress-step-label">' + step.label + '</span>' +
                    '<span class="progress-step-hint">' + step.detail + '</span>' +
                '</span>';
            this.list.appendChild(item);
        }
    }

    setStep(stepId, state, detailText) {
        const item = this.list.querySelector('[data-step="' + stepId + '"]');
        if (item) {
            item.className = 'progress-step ' + state;
        }
        const step = SAVE_STEPS.find((s) => s.id === stepId);
        if (detailText) {
            this.detail.textContent = detailText;
        } else if (step) {
            this.detail.textContent = step.detail;
        }
    }

    fail(stepId, message) {
        if (stepId) this.setStep(stepId, 'error', message);
        this.busy = false;
        this.overlay.classList.remove('busy');
        this.progressPanel.setAttribute('aria-busy', 'false');
        this.footer.hidden = false;
        this.cancelBtn.disabled = false;
        this.confirmBtn.disabled = false;
        this.confirmBtn.textContent = 'Try again';
        this.title.textContent = AK_DESKTOP ? 'Save failed' : 'Download failed';
        this.confirmBtn.focus();
    }

    resetConfirmControls() {
        this.confirmBtn.textContent = SAVE_ACTION;
    }
}

const saveProgress = new SaveProgress();

function closeSaveModal() {
    if (saveProgress.busy) return;
    closeDialog(document.getElementById('save-modal'));
    saveProgress.resetConfirmControls();
}

function postSaveStep(step) {
    return fetch('/api/save/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step: step }),
    }).then(async (resp) => {
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            const err = new Error(data.error || 'Save step failed');
            err.data = data;
            throw err;
        }
        return data;
    });
}

async function runSavePipeline() {
    saveProgress.startProgress();
    saveProgress.setStep('cleanup', 'active');

    try {
        const cleanup = await postSaveStep('cleanup');
        saveProgress.setStep(
            'cleanup',
            'done',
            'Cleaned ' + cleanup.cleaned_count + ' stale link' +
                (cleanup.cleaned_count === 1 ? '' : 's') + '.',
        );

        saveProgress.setStep('apply', 'active');
        const apply = await postSaveStep('apply');
        saveProgress.setStep(
            'apply',
            'done',
            'Updated ' + apply.updated_count + ' KeePass entr' +
                (apply.updated_count === 1 ? 'y' : 'ies') + '.',
        );

        saveProgress.setStep('build', 'active');
        await postSaveStep('build');
        saveProgress.setStep('build', 'done', 'Merged database ready.');

        saveProgress.setStep('download', 'active');

        let completeSummary;
        if (window.AK_DESKTOP && window.pywebview && window.pywebview.api) {
            const res = await window.pywebview.api.download_merged('keepass-merged.kdbx');
            if (!res || !res.success) {
                throw new Error((res && res.error) || (AK_DESKTOP ? 'Save failed' : 'Download failed'));
            }
            completeSummary = res.summary || {
                total: '0',
                otp: '0',
                updated: '0',
                cleaned: '0',
            };
            saveProgress.setStep('download', 'done', 'Saved. Session wiped.');
        } else {
            const resp = await fetch('/api/save/download', { method: 'POST' });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.error || 'Download failed');
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

            completeSummary = {
                total: resp.headers.get('X-Total-Entries') || '0',
                otp: resp.headers.get('X-Otp-Entries') || '0',
                updated: resp.headers.get('X-Updated-Count') || '0',
                cleaned: resp.headers.get('X-Cleaned-Count') || '0',
            };
            saveProgress.setStep('download', 'done', 'Download started. Session wiped.');
        }

        saveProgress.busy = false;
        saveProgress.overlay.classList.remove('busy');
        closeDialog(document.getElementById('save-modal'));
        saveProgress.resetConfirmControls();

        showCompleteView(completeSummary);
    } catch (err) {
        const active = saveProgress.list.querySelector('.progress-step.active');
        const stepId = active ? active.dataset.step : 'download';
        saveProgress.fail(stepId, err.message || 'Save failed');
        showToast(err.message || 'Save failed', 'error');
    }
}

function openEndSessionModal() {
    openDialog(
        document.getElementById('end-session-modal'),
        document.getElementById('end-session-confirm-btn'),
    );
}

function closeEndSessionModal() {
    closeDialog(document.getElementById('end-session-modal'));
}

async function endSessionAndLeave() {
    try {
        await fetch('/api/session/end', { method: 'POST' });
    } catch (e) { /* still leave */ }
    window.location.href = '/';
}

document.getElementById('save-btn').addEventListener('click', () => {
    saveProgress.resetConfirmControls();
    saveProgress.openConfirm();
});

document.getElementById('save-cancel-btn').addEventListener('click', closeSaveModal);
document.getElementById('save-confirm-btn').addEventListener('click', () => {
    runSavePipeline();
});
document.getElementById('save-modal').addEventListener('click', (e) => {
    if (e.target.id === 'save-modal' && !saveProgress.busy) closeSaveModal();
});

document.getElementById('end-session-btn').addEventListener('click', openEndSessionModal);
document.getElementById('end-session-cancel-btn').addEventListener('click', closeEndSessionModal);
document.getElementById('end-session-confirm-btn').addEventListener('click', endSessionAndLeave);
document.getElementById('end-session-modal').addEventListener('click', (e) => {
    if (e.target.id === 'end-session-modal') closeEndSessionModal();
});

document.getElementById('complete-restart-btn').addEventListener('click', () => {
    window.location.href = '/';
});

document.getElementById('picker-modal').addEventListener('click', (e) => {
    if (e.target.id === 'picker-modal') closePicker();
});
document.getElementById('picker-cancel-btn').addEventListener('click', closePicker);

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
