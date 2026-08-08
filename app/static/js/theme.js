(function () {
    const STORAGE_KEY = 'ak-theme';
    const PREFS = ['system', 'light', 'dark'];

    // pywebview/WebKitGTK may lack localStorage; keep an in-memory fallback.
    let memoryPref = null;

    function readStoredPreference() {
        try {
            if (typeof localStorage === 'undefined') return null;
            const stored = localStorage.getItem(STORAGE_KEY);
            return PREFS.includes(stored) ? stored : null;
        } catch (_) {
            return null;
        }
    }

    function writeStoredPreference(pref) {
        try {
            if (typeof localStorage === 'undefined') return;
            localStorage.setItem(STORAGE_KEY, pref);
        } catch (_) {
            /* ignore */
        }
    }

    function getPreference() {
        const attr = document.documentElement.getAttribute('data-theme-pref');
        if (PREFS.includes(attr)) return attr;
        if (PREFS.includes(memoryPref)) return memoryPref;
        return readStoredPreference() || 'system';
    }

    function resolveTheme(pref) {
        if (pref === 'light' || pref === 'dark') return pref;
        // Desktop shell injects host OS theme; WebKitGTK matchMedia is unreliable.
        if (window.AK_SYSTEM_THEME === 'light' || window.AK_SYSTEM_THEME === 'dark') {
            return window.AK_SYSTEM_THEME;
        }
        if (window.AK_DESKTOP) {
            return 'dark';
        }
        try {
            if (window.matchMedia('(prefers-color-scheme: light)').matches) return 'light';
            if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
        } catch (_) {
            /* ignore */
        }
        return 'dark';
    }

    function notifyDesktopNativeTheme(resolved) {
        if (!window.AK_DESKTOP) return;
        const api = window.pywebview && window.pywebview.api;
        if (!api || typeof api.set_prefer_dark !== 'function') return;
        try {
            const result = api.set_prefer_dark(resolved !== 'light');
            if (result && typeof result.then === 'function') {
                result.catch(function () { /* ignore */ });
            }
        } catch (_) {
            /* ignore */
        }
    }

    function applyTheme(pref) {
        const theme = resolveTheme(pref);
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.setAttribute('data-theme-pref', pref);
        notifyDesktopNativeTheme(theme);
        return theme;
    }

    function setPreference(pref) {
        if (!PREFS.includes(pref)) pref = 'system';
        memoryPref = pref;
        writeStoredPreference(pref);
        applyTheme(pref);
        syncToggle(pref);
    }

    function cyclePreference() {
        const current = getPreference();
        const idx = PREFS.indexOf(current);
        const next = PREFS[((idx < 0 ? 0 : idx) + 1) % PREFS.length];
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
        memoryPref = pref;
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
