/**
 * scinotation.js
 * Handles ScientificNumberInput fields (tagged data-scinotation="true"):
 *   • Re-formats value to scientific notation on blur.
 *   • Step ▲/▼ buttons increment/decrement the value.
 *
 * Format rules (mirror Python format_sci()):
 *   |v| < 1e-3 or |v| >= 1e6  →  "1.23 E-6"
 *   otherwise                  →  plain decimal, trailing zeros stripped
 */

(function () {
    var SCI_LOWER = 1e-3;
    var SCI_UPPER = 1e6;

    // ------------------------------------------------------------------ //
    // Formatting / parsing
    // ------------------------------------------------------------------ //

    function formatSci(v) {
        if (!isFinite(v)) return String(v);
        if (v === 0) return '0';
        var absV = Math.abs(v);
        if (absV < SCI_LOWER || absV >= SCI_UPPER) {
            var exp = Math.floor(Math.log10(absV));
            var mantissa = Math.round((v / Math.pow(10, exp)) * 100) / 100;
            var sign = exp >= 0 ? '+' : '';
            return mantissa + ' E' + sign + exp;
        }
        return parseFloat(v.toPrecision(6)).toString();
    }

    function parseSci(text) {
        if (!text || text.trim() === '') return NaN;
        var s = text.replace(/\s/g, '').replace(/E/gi, 'e');
        return parseFloat(s);
    }

    // ------------------------------------------------------------------ //
    // React-aware value setter
    // ------------------------------------------------------------------ //

    var nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, 'value'
    ).set;

    function setInputValue(input, newValue) {
        if (input.value === newValue) return;
        nativeSetter.call(input, newValue);
        input.dispatchEvent(new Event('input', { bubbles: true }));
    }

    // ------------------------------------------------------------------ //
    // Blur: re-format
    // ------------------------------------------------------------------ //

    function reformatInput(input) {
        var num = parseSci(input.value);
        if (isNaN(num)) return;
        setInputValue(input, formatSci(num));
    }

    function attachBlurListener(input) {
        if (input._sciBlurBound) return;
        input._sciBlurBound = true;
        input.addEventListener('blur', function () { reformatInput(input); });
    }

    // ------------------------------------------------------------------ //
    // Step buttons: ▲ / ▼
    // ------------------------------------------------------------------ //

    function computeStep(input, currentValue) {
        var stepAttr = input.dataset.step;
        if (stepAttr && stepAttr !== 'auto' && stepAttr !== 'None') {
            var s = parseFloat(stepAttr);
            if (!isNaN(s) && s > 0) return s;
        }
        // Auto: one order of magnitude below current value
        if (!isFinite(currentValue) || currentValue === 0) return 1;
        var exp = Math.floor(Math.log10(Math.abs(currentValue)));
        return Math.pow(10, exp - 1);
    }

    document.addEventListener('mousedown', function (e) {
        var btn = e.target.closest('.sci-num-btn');
        if (!btn) return;

        // Find the sibling input inside the same Mantine Input wrapper
        var wrapper = btn.closest('[class*="Input-wrapper"], [class*="inputWrapper"]');
        if (!wrapper) {
            // Fallback: walk up until we find a parent that contains the input
            var parent = btn.parentElement;
            while (parent && !wrapper) {
                if (parent.querySelector('input[data-scinotation]')) wrapper = parent;
                parent = parent.parentElement;
            }
        }
        if (!wrapper) return;

        var input = wrapper.querySelector('input[data-scinotation="true"]');
        if (!input || input.disabled) return;

        e.preventDefault();  // prevent input from losing focus

        var current = parseSci(input.value);
        if (isNaN(current)) current = 0;

        var step = computeStep(input, current);
        var isUp = btn.classList.contains('sci-num-btn-up');
        var newVal = isUp ? current + step : current - step;

        // Clamp to min/max if specified
        var minAttr = input.dataset.min;
        var maxAttr = input.dataset.max;
        if (minAttr && minAttr !== 'None') newVal = Math.max(parseFloat(minAttr), newVal);
        if (maxAttr && maxAttr !== 'None') newVal = Math.min(parseFloat(maxAttr), newVal);

        setInputValue(input, formatSci(newVal));
    }, true);

    // ------------------------------------------------------------------ //
    // Attach blur listeners to all tagged inputs (existing + future)
    // ------------------------------------------------------------------ //

    function scanAndAttach() {
        document.querySelectorAll('input[data-scinotation="true"]')
            .forEach(attachBlurListener);
    }

    var observer = new MutationObserver(function (mutations) {
        if (mutations.some(function (m) { return m.addedNodes.length > 0; })) {
            scanAndAttach();
        }
    });

    function init() {
        scanAndAttach();
        observer.observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
