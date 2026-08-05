const UPLOAD_STEPS = [
    {
        id: 'upload',
        label: 'Uploading files to server',
        detail: 'Sending your encrypted Aegis backup, KeePass database, and passwords.',
    },
    {
        id: 'validate',
        label: 'Validating file formats',
        detail: 'Checking encrypted Aegis JSON and KeePass .kdbx signatures.',
    },
    {
        id: 'decrypt_aegis',
        label: 'Decrypting Aegis backup',
        detail: 'Deriving keys and decrypting TOTP entries in server memory.',
    },
    {
        id: 'open_keepass',
        label: 'Opening KeePass database',
        detail: 'Unlocking your .kdbx file and loading entries (excluding recycle bin).',
    },
    {
        id: 'match',
        label: 'Matching entries',
        detail: 'Running fuzzy matching between Aegis and KeePass entries.',
    },
    {
        id: 'done',
        label: 'Preparing review',
        detail: 'Redirecting to the match review screen.',
    },
];

function setupDropZone(zoneId, inputId, nameId) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    const nameEl = document.getElementById(nameId);

    function setFile(file) {
        if (!file) return;
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        nameEl.textContent = file.name;
        zone.classList.add('has-file');
    }

    input.addEventListener('change', () => {
        if (input.files[0]) setFile(input.files[0]);
    });

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
    });
}

class UploadProgress {
    constructor() {
        this.panel = document.getElementById('upload-progress');
        this.list = document.getElementById('upload-progress-steps');
        this.detail = document.getElementById('upload-progress-detail');
        this.form = document.getElementById('upload-form');
        this.states = new Map();
    }

    show() {
        this.panel.hidden = false;
        this.panel.setAttribute('aria-busy', 'true');
        this.form.hidden = true;
        this.list.innerHTML = '';
        this.states.clear();

        for (const step of UPLOAD_STEPS) {
            this.states.set(step.id, 'pending');
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

    hide() {
        this.panel.hidden = true;
        this.panel.setAttribute('aria-busy', 'false');
        this.form.hidden = false;
    }

    setStep(stepId, state, detailText) {
        if (this.states.has(stepId)) {
            this.states.set(stepId, state);
        }
        const item = this.list.querySelector('[data-step="' + stepId + '"]');
        if (item) {
            item.className = 'progress-step ' + state;
        }
        const step = UPLOAD_STEPS.find((s) => s.id === stepId);
        if (detailText) {
            this.detail.textContent = detailText;
        } else if (step) {
            this.detail.textContent = step.detail;
        }
    }

    setUploadPercent(loaded, total) {
        if (!total) return;
        const pct = Math.min(100, Math.round((loaded / total) * 100));
        this.setStep(
            'upload',
            'active',
            'Uploading files to server (' + pct + '%)…',
        );
    }
}

const uploadProgress = new UploadProgress();

function postJson(url, body) {
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    }).then(async (resp) => {
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            const err = new Error(data.error || 'Request failed');
            err.response = resp;
            err.data = data;
            throw err;
        }
        return data;
    });
}

function uploadFormData(formData, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload');
        xhr.responseType = 'json';

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable && onProgress) {
                onProgress(e.loaded, e.total);
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(xhr.response || {});
                return;
            }
            const data = xhr.response || {};
            const err = new Error(data.error || 'Upload failed');
            err.status = xhr.status;
            err.data = data;
            reject(err);
        });

        xhr.addEventListener('error', () => {
            reject(new Error('Network error during upload'));
        });

        xhr.send(formData);
    });
}

async function runProcessingPipeline(formData) {
    uploadProgress.show();
    uploadProgress.setStep('upload', 'active');

    await uploadFormData(formData, (loaded, total) => {
        uploadProgress.setUploadPercent(loaded, total);
    });
    uploadProgress.setStep('upload', 'done');
    uploadProgress.setStep('validate', 'active');
    uploadProgress.setStep('validate', 'done');

    uploadProgress.setStep('decrypt_aegis', 'active');
    const decryptResult = await postJson('/api/upload/process', { step: 'decrypt_aegis' });
    uploadProgress.setStep(
        'decrypt_aegis',
        'done',
        'Decrypted ' + decryptResult.aegis_count + ' Aegis TOTP entries.',
    );

    uploadProgress.setStep('open_keepass', 'active');
    const keepassResult = await postJson('/api/upload/process', { step: 'open_keepass' });
    uploadProgress.setStep(
        'open_keepass',
        'done',
        'Loaded ' + keepassResult.keepass_count + ' KeePass entries.',
    );

    uploadProgress.setStep('match', 'active');
    const matchResult = await postJson('/api/upload/process', { step: 'match' });
    uploadProgress.setStep(
        'match',
        'done',
        'Matched ' + matchResult.stats.matched + ' of ' + matchResult.stats.aegis_total + ' Aegis entries.',
    );

    uploadProgress.setStep('done', 'active');
    uploadProgress.setStep('done', 'done', 'Opening review…');

    window.location.href = matchResult.redirect || '/review';
}

setupDropZone('aegis-drop', 'aegis-input', 'aegis-name');
setupDropZone('keepass-drop', 'keepass-input', 'keepass-name');

document.querySelectorAll('[data-password-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
        const input = document.getElementById(btn.getAttribute('data-password-toggle'));
        if (!input) return;
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        btn.setAttribute('aria-pressed', show ? 'true' : 'false');
        btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    });
});

const keyfileInput = document.getElementById('keyfile-input');
const keyfileBtn = document.getElementById('keyfile-btn');
const keyfileName = document.getElementById('keyfile-name');

keyfileBtn.addEventListener('click', () => keyfileInput.click());

keyfileInput.addEventListener('change', () => {
    const file = keyfileInput.files[0];
    keyfileName.textContent = file ? file.name : 'Only if your database requires a keyfile';
});

document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const aegis = document.getElementById('aegis-input').files[0];
    const keepass = document.getElementById('keepass-input').files[0];
    const aegisPassword = document.getElementById('aegis-password-input').value;
    const keepassPassword = document.getElementById('keepass-password-input').value;

    const aegisPasswordInput = document.getElementById('aegis-password-input');
    const keepassPasswordInput = document.getElementById('keepass-password-input');
    const aegisInput = document.getElementById('aegis-input');
    const keepassInput = document.getElementById('keepass-input');

    aegisPasswordInput.removeAttribute('aria-invalid');
    keepassPasswordInput.removeAttribute('aria-invalid');
    aegisInput.removeAttribute('aria-invalid');
    keepassInput.removeAttribute('aria-invalid');

    if (!aegis || !keepass) {
        showToast('Please select both files.', 'error');
        if (!aegis) {
            aegisInput.setAttribute('aria-invalid', 'true');
            aegisInput.focus();
        } else {
            keepassInput.setAttribute('aria-invalid', 'true');
            keepassInput.focus();
        }
        return;
    }
    if (!aegisPassword) {
        showToast('Please enter the Aegis backup password.', 'error');
        aegisPasswordInput.setAttribute('aria-invalid', 'true');
        aegisPasswordInput.focus();
        return;
    }
    if (!keepassPassword) {
        showToast('Please enter the KeePass master password.', 'error');
        keepassPasswordInput.setAttribute('aria-invalid', 'true');
        keepassPasswordInput.focus();
        return;
    }

    const btn = document.getElementById('upload-btn');
    btn.disabled = true;
    btn.textContent = 'Processing…';

    const body = new FormData(e.target);

    try {
        await runProcessingPipeline(body);
    } catch (err) {
        uploadProgress.hide();
        showToast(err.message || 'Upload failed', 'error');
        btn.disabled = false;
        btn.textContent = 'Continue to review';
    }
});
