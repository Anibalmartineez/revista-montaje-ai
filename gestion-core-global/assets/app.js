(function () {
    function getSectionIdFromHash(hash) {
        if (!hash) {
            return '';
        }
        return hash.replace('#', '');
    }

    function getStoredSection() {
        try {
            return window.localStorage.getItem('gc_active_section') || '';
        } catch (error) {
            return '';
        }
    }

    function storeSection(sectionId) {
        if (!sectionId) {
            return;
        }
        try {
            window.localStorage.setItem('gc_active_section', sectionId);
        } catch (error) {
            // ignore storage errors
        }
    }

    function setActiveSection(container, sectionId, options) {
        if (!container || !sectionId) {
            return false;
        }
        var button = container.querySelector('.gc-dashboard-button[data-gc-target="' + sectionId + '"]');
        var section = container.querySelector('.gc-dashboard-section[data-gc-section="' + sectionId + '"]');
        if (!button || !section) {
            return false;
        }
        var buttons = container.querySelectorAll('.gc-dashboard-button');
        var sections = container.querySelectorAll('.gc-dashboard-section');
        buttons.forEach(function (item) {
            item.classList.remove('is-active');
        });
        sections.forEach(function (item) {
            item.classList.remove('is-active');
        });
        button.classList.add('is-active');
        section.classList.add('is-active');

        if (options && options.updateHash) {
            if (window.history && window.history.pushState) {
                window.history.pushState(null, '', '#' + sectionId);
            } else {
                window.location.hash = sectionId;
            }
        }

        if (options && options.persist) {
            storeSection(sectionId);
        }

        return true;
    }

    function scrollToSection(container, sectionId) {
        if (!container || !sectionId || !window.requestAnimationFrame) {
            return;
        }
        var section = container.querySelector('.gc-dashboard-section[data-gc-section="' + sectionId + '"]');
        if (!section || typeof section.scrollIntoView !== 'function') {
            return;
        }
        window.requestAnimationFrame(function () {
            section.scrollIntoView();
        });
    }

    function getDefaultSection(container) {
        if (!container) {
            return '';
        }
        var preferred = container.querySelector('.gc-dashboard-section[data-gc-section="movimientos"]');
        if (preferred) {
            return 'movimientos';
        }
        var first = container.querySelector('.gc-dashboard-section[data-gc-section]');
        return first ? first.getAttribute('data-gc-section') || '' : '';
    }

    function handleNavClick(event) {
        var eventTarget = event.target;
        var target = eventTarget instanceof Element ? eventTarget.closest('.gc-dashboard-button') : null;
        if (!target) {
            return;
        }
        var container = target.closest('.gc-dashboard');
        var sectionId = target.getAttribute('data-gc-target') || getSectionIdFromHash(target.getAttribute('href') || '');
        if (!container || !sectionId) {
            return;
        }
        event.preventDefault();
        setActiveSection(container, sectionId, { updateHash: true, persist: true });
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

    function toggleDeudaFields(scope) {
        var selects = (scope || document).querySelectorAll('select[name="tipo_deuda"]');
        selects.forEach(function (select) {
            var form = select.closest('form');
            if (!form) {
                return;
            }
            var update = function () {
                var value = select.value;
                var fields = form.querySelectorAll('[data-gc-show-deuda]');
                fields.forEach(function (field) {
                    var expected = field.getAttribute('data-gc-show-deuda') || '';
                    var allowed = expected.split(',').map(function (item) {
                        return item.trim();
                    }).filter(Boolean);
                    var shouldShow = allowed.indexOf(value) !== -1;
                    field.style.display = shouldShow ? '' : 'none';
                });
            };
            select.addEventListener('change', update);
            update();
        });
    }

    function toggleFrecuenciaFields(scope) {
        var selects = (scope || document).querySelectorAll('select[name="frecuencia"]');
        selects.forEach(function (select) {
            var form = select.closest('form');
            if (!form) {
                return;
            }
            var update = function () {
                var value = select.value;
                var fields = form.querySelectorAll('[data-gc-show-frecuencia]');
                fields.forEach(function (field) {
                    var expected = field.getAttribute('data-gc-show-frecuencia') || '';
                    var allowed = expected.split(',').map(function (item) {
                        return item.trim();
                    }).filter(Boolean);
                    var shouldShow = allowed.indexOf(value) !== -1;
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

    function initDashboardNavigation() {
        var dashboards = document.querySelectorAll('.gc-dashboard');
        dashboards.forEach(function (container) {
            var hashSection = getSectionIdFromHash(window.location.hash);
            var storedSection = getStoredSection();
            var defaultSection = getDefaultSection(container);
            var targetSection = '';

            if (hashSection && container.querySelector('.gc-dashboard-section[data-gc-section="' + hashSection + '"]')) {
                targetSection = hashSection;
            } else if (storedSection && container.querySelector('.gc-dashboard-section[data-gc-section="' + storedSection + '"]')) {
                targetSection = storedSection;
            } else {
                targetSection = defaultSection;
            }

            if (targetSection) {
                setActiveSection(container, targetSection, { updateHash: false, persist: true });
                if (targetSection === hashSection) {
                    scrollToSection(container, targetSection);
                }
            }
        });

        window.addEventListener('hashchange', function () {
            var sectionId = getSectionIdFromHash(window.location.hash);
            if (!sectionId) {
                return;
            }
            dashboards.forEach(function (container) {
                if (setActiveSection(container, sectionId, { updateHash: false, persist: true })) {
                    scrollToSection(container, sectionId);
                }
            });
        });
    }

    function init() {
        document.addEventListener('click', handleNavClick);
        toggleConditionalFields(document);
        toggleDeudaFields(document);
        toggleFrecuenciaFields(document);
        initPendingAmountAutofill();
        initDashboardNavigation();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
