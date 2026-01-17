(function () {
    function setActiveNav(link) {
        if (!link) {
            return;
        }
        var container = link.closest('.gc-dashboard');
        if (!container) {
            return;
        }
        var links = container.querySelectorAll('.gc-dashboard-button');
        links.forEach(function (item) {
            item.classList.remove('is-active');
        });
        link.classList.add('is-active');
    }

    function handleNavClick(event) {
        var target = event.target.closest('.gc-dashboard-button');
        if (!target) {
            return;
        }
        setActiveNav(target);
    }

    function toggleConditionalFields(scope) {
        var selects = (scope || document).querySelectorAll('select[name="tipo"]');
        selects.forEach(function (select) {
            var form = select.closest('form');
            if (!form) {
                return;
            }
            var update = function () {
                var value = select.value;
                var fields = form.querySelectorAll('[data-gc-show]');
                fields.forEach(function (field) {
                    var expected = field.getAttribute('data-gc-show');
                    var shouldShow = expected === value;
                    field.style.display = shouldShow ? '' : 'none';
                });
            };
            select.addEventListener('change', update);
            update();
        });
    }

    function initPendingAmountAutofill() {
        if (!window.gcCoreGlobal || !window.gcCoreGlobal.ajaxUrl) {
            return;
        }

        var forms = document.querySelectorAll('form.gc-form-movimientos');
        forms.forEach(function (form) {
            var montoInput = form.querySelector('input[name="monto"]');
            var documentoSelect = form.querySelector('select[name="documento_id"]');
            var deudaSelect = form.querySelector('select[name="deuda_id"]');

            if (!montoInput || (!documentoSelect && !deudaSelect)) {
                return;
            }

            var pendingRequest = null;
            var debounceTimer = null;

            var requestSaldo = function (entityType, entityId) {
                if (!entityId) {
                    return;
                }

                if (pendingRequest) {
                    pendingRequest.abort();
                }
                if (debounceTimer) {
                    window.clearTimeout(debounceTimer);
                }

                debounceTimer = window.setTimeout(function () {
                    pendingRequest = new AbortController();
                    var payload = new URLSearchParams({
                        action: 'gc_get_pending_amount',
                        entity_type: entityType,
                        entity_id: entityId,
                        _ajax_nonce: window.gcCoreGlobal.pendingAmountNonce
                    });

                    fetch(window.gcCoreGlobal.ajaxUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
                        },
                        body: payload.toString(),
                        signal: pendingRequest.signal
                    })
                        .then(function (response) {
                            return response.json();
                        })
                        .then(function (data) {
                            if (!data || !data.ok) {
                                return;
                            }
                            var saldo = parseFloat(data.saldo);
                            if (Number.isNaN(saldo)) {
                                return;
                            }
                            if (saldo > 0) {
                                montoInput.value = saldo.toFixed(2);
                            } else if (saldo === 0) {
                                montoInput.value = '0';
                            }
                        })
                        .catch(function (error) {
                            if (error && error.name === 'AbortError') {
                                return;
                            }
                        });
                }, 200);
            };

            if (documentoSelect) {
                documentoSelect.addEventListener('change', function () {
                    requestSaldo('documento', documentoSelect.value);
                });
            }

            if (deudaSelect) {
                deudaSelect.addEventListener('change', function () {
                    requestSaldo('deuda', deudaSelect.value);
                });
            }
        });
    }

    function init() {
        document.addEventListener('click', handleNavClick);
        toggleConditionalFields(document);
        initPendingAmountAutofill();
        if (window.location.hash) {
            var initial = document.querySelector('.gc-dashboard-button[href="' + window.location.hash + '"]');
            if (initial) {
                setActiveNav(initial);
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
