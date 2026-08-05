(function (global) {
    let hideTimer = null;

    function showToast(msg, type) {
        const t = document.getElementById('toast');
        if (!t) return;
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
        t.textContent = msg;
        // Restart entrance when a toast replaces another.
        t.className = 'toast';
        void t.offsetWidth;
        t.className = 'toast show' + (type ? ' ' + type : '');
        hideTimer = setTimeout(() => {
            t.className = 'toast';
            hideTimer = null;
        }, 5000);
    }

    global.showToast = showToast;
})(window);
