(function () {
    const STORAGE_KEY = 'ak-theme';
    const PREFS = ['system', 'light', 'dark'];

    function getPreference() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (PREFS.includes(stored)) return stored;
        } catch (_) {
            /* ignore */
        }
        return 'system';
    }

    function resolveTheme(pref) {
        if (pref === 'light' || pref === 'dark') return pref;
        try {
            if (window.matchMedia('(prefers-color-scheme: light)').matches) return 'light';
            if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
        } catch (_) {
            /* ignore */
        }
        return 'dark';
    }

    function applyTheme(pref) {
        const theme = resolveTheme(pref);
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.setAttribute('data-theme-pref', pref);
        return theme;
    }

    function setPreference(pref) {
        if (!PREFS.includes(pref)) pref = 'system';
        try {
            localStorage.setItem(STORAGE_KEY, pref);
        } catch (_) {
            /* ignore */
        }
        applyTheme(pref);
        syncToggle(pref);
    }

    function cyclePreference() {
        const current = getPreference();
        const next = PREFS[(PREFS.indexOf(current) + 1) % PREFS.length];
        setPreference(next);
    }

    function labelFor(pref) {
        if (pref === 'light') return 'Light';
        if (pref === 'dark') return 'Dark';
        return 'System';
    }

    function syncToggle(pref) {
        const btn = document.getElementById('theme-toggle');
        if (!btn) return;
        const resolved = resolveTheme(pref);
        const label = labelFor(pref);
        btn.dataset.pref = pref;
        btn.dataset.theme = resolved;
        btn.setAttribute(
            'aria-label',
            'Color theme: ' + label + '. Click to change.'
        );
        btn.title = 'Theme: ' + label + ' (click to cycle System, Light, Dark)';
        const labelEl = document.getElementById('theme-toggle-label');
        if (labelEl) labelEl.textContent = label;
    }

    function init() {
        const pref = getPreference();
        applyTheme(pref);
        syncToggle(pref);

        const btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.addEventListener('click', cyclePreference);
        }

        try {
            const mq = window.matchMedia('(prefers-color-scheme: dark)');
            const onChange = () => {
                if (getPreference() === 'system') {
                    applyTheme('system');
                    syncToggle('system');
                }
            };
            if (typeof mq.addEventListener === 'function') {
                mq.addEventListener('change', onChange);
            } else if (typeof mq.addListener === 'function') {
                mq.addListener(onChange);
            }
        } catch (_) {
            /* ignore */
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
