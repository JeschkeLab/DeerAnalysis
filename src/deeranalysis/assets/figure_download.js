// Routes Plotly's modebar "Download plot as image" button through
// pywebview's native save dialog. Intercepts the camera button click in
// the document-level capture phase. Shows a format picker (SVG / PNG)
// before opening the native save dialog so the choice is always explicit.
(function () {
    function figureName(gd) {
        var title = gd && gd.layout && gd.layout.title;
        if (title && typeof title === 'string') return title;
        if (title && title.text) return title.text;
        return 'figure';
    }

    function isDownloadButton(btn) {
        if (btn.hasAttribute('data-pywv-download')) return true;
        var title = (btn.getAttribute('data-title') || '').toLowerCase();
        return title.indexOf('download') !== -1 ||
               title.indexOf('save plot') !== -1 ||
               title.indexOf('image') !== -1;
    }

    function showFormatPicker(svgUrl, pngUrl, name) {
        var existing = document.getElementById('pywv-fmt-picker');
        if (existing) existing.remove();

        var overlay = document.createElement('div');
        overlay.id = 'pywv-fmt-overlay';
        overlay.style.cssText =
            'position:fixed;inset:0;z-index:9998;background:rgba(0,0,0,0.3)';

        var picker = document.createElement('div');
        picker.id = 'pywv-fmt-picker';
        picker.style.cssText =
            'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);' +
            'background:#fff;border-radius:8px;padding:20px 24px;' +
            'box-shadow:0 8px 32px rgba(0,0,0,0.2);z-index:9999;' +
            'font-family:system-ui,sans-serif;text-align:center;min-width:220px';
        picker.innerHTML =
            '<p style="margin:0 0 16px;font-size:15px;font-weight:600;color:#212529">' +
                'Save figure as&hellip;</p>' +
            '<div style="display:flex;gap:10px;justify-content:center">' +
                '<button id="pywv-save-svg" style="' +
                    'flex:1;padding:9px 0;cursor:pointer;border:1.5px solid #228be6;' +
                    'color:#228be6;background:#fff;border-radius:6px;font-size:14px;' +
                    'font-weight:600">SVG</button>' +
                '<button id="pywv-save-png" style="' +
                    'flex:1;padding:9px 0;cursor:pointer;border:1.5px solid #868e96;' +
                    'color:#495057;background:#fff;border-radius:6px;font-size:14px">' +
                    'PNG</button>' +
            '</div>';

        function dismiss() {
            overlay.remove();
            picker.remove();
            document.removeEventListener('keydown', onKey, true);
        }

        function onKey(e) {
            if (e.key === 'Escape') dismiss();
        }

        overlay.addEventListener('click', dismiss);
        document.addEventListener('keydown', onKey, true);

        picker.querySelector('#pywv-save-svg').addEventListener('click', function (e) {
            e.stopPropagation();
            dismiss();
            window.pywebview.api.save_figure(svgUrl, name, 'svg');
        });
        picker.querySelector('#pywv-save-png').addEventListener('click', function (e) {
            e.stopPropagation();
            dismiss();
            window.pywebview.api.save_figure(pngUrl, name, 'png');
        });

        document.body.appendChild(overlay);
        document.body.appendChild(picker);
    }

    function handle(e) {
        var t = e.target;
        if (!t || !t.closest) return;
        var btn = t.closest('.modebar-btn');
        if (!btn || !isDownloadButton(btn)) return;
        var gd = btn.closest('.js-plotly-plot') || btn.closest('.plot-container');
        if (!gd || !window.Plotly) return;
        if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.save_figure) {
            window.alert('Figure download unavailable: pywebview API not loaded.');
            return;
        }

        e.preventDefault();
        e.stopImmediatePropagation();

        var layout = gd._fullLayout || {};
        var width = layout.width || 800;
        var height = layout.height || 600;
        var name = figureName(gd);

        Promise.all([
            window.Plotly.toImage(gd, {format: 'svg', width: width, height: height}),
            window.Plotly.toImage(gd, {format: 'png', width: width, height: height, scale: 2})
        ]).then(function (urls) {
            showFormatPicker(urls[0], urls[1], name);
        }).catch(function (err) {
            console.error('[figure_download] toImage failed:', err);
            window.alert('Could not render figure: ' + (err && err.message ? err.message : err));
        });
    }

    function patchDownloadTooltips(root) {
        (root || document).querySelectorAll('.modebar-btn').forEach(function (btn) {
            if (isDownloadButton(btn)) {
                btn.setAttribute('data-title', 'Save as SVG or PNG');
                btn.setAttribute('data-pywv-download', '1');
            }
        });
    }

    new MutationObserver(function () {
        patchDownloadTooltips();
    }).observe(document.body, {childList: true, subtree: true});

    document.addEventListener('click', handle, true);
})();
