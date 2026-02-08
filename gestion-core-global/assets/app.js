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
        var hash = target.getAttribute('href');
        if (hash) {
            var dashboard = target.closest('.gc-dashboard');
            openModuleById(dashboard, hash.replace('#', ''), false);
        }
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

    function reorderPanelBody(panelBody) {
        if (!panelBody) {
            return;
        }
        var tableWrap = panelBody.querySelector('.gc-table-wrap');
        var filterForm = panelBody.querySelector('.gc-form-inline');
        var createForm = panelBody.querySelector('.gc-form:not(.gc-form-inline)');
        if (!tableWrap || !createForm) {
            return;
        }
        if (filterForm) {
            panelBody.insertBefore(filterForm, createForm);
        }
        panelBody.insertBefore(tableWrap, createForm);
    }

    function setModuleState(module, isOpen) {
        if (!module) {
            return;
        }
        var body = module.querySelector('.gc-module__body');
        var toggle = module.querySelector('.gc-module__toggle');
        module.classList.toggle('is-open', isOpen);
        if (body) {
            body.hidden = !isOpen;
        }
        if (toggle) {
            toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        }
    }

    function openModuleById(dashboard, moduleId, persist) {
        if (!dashboard || !moduleId) {
            return;
        }
        var modules = dashboard.querySelectorAll('.gc-module');
        if (!modules.length) {
            return;
        }
        var found = null;
        modules.forEach(function (module) {
            var currentId = module.getAttribute('data-gc-module');
            var isTarget = currentId === moduleId;
            if (isTarget) {
                found = module;
            }
            setModuleState(module, isTarget);
        });
        if (found && persist !== false && window.localStorage) {
            try {
                window.localStorage.setItem('gc_dashboard_module', moduleId);
            } catch (error) {
                // ignore storage errors
            }
        }
    }

    function initModules() {
        var dashboards = document.querySelectorAll('.gc-dashboard');
        if (!dashboards.length) {
            return;
        }
        dashboards.forEach(function (dashboard) {
            var modules = dashboard.querySelectorAll('.gc-module');
            if (!modules.length) {
                return;
            }
            modules.forEach(function (module) {
                var panelBody = module.querySelector('.gc-panel-body');
                reorderPanelBody(panelBody);
                var toggle = module.querySelector('.gc-module__toggle');
                if (!toggle) {
                    return;
                }
                toggle.addEventListener('click', function () {
                    var moduleId = module.getAttribute('data-gc-module');
                    var isOpen = !module.classList.contains('is-open');
                    if (isOpen && moduleId) {
                        openModuleById(dashboard, moduleId, true);
                    } else {
                        setModuleState(module, false);
                    }
                });
            });

            var activeId = '';
            if (window.location.hash) {
                activeId = window.location.hash.replace('#', '');
            } else if (window.localStorage) {
                try {
                    activeId = window.localStorage.getItem('gc_dashboard_module') || '';
                } catch (error) {
                    activeId = '';
                }
            }
            if (!activeId) {
                var first = modules[0].getAttribute('data-gc-module');
                if (first) {
                    activeId = first;
                }
            }
            if (activeId) {
                openModuleById(dashboard, activeId, false);
            }
        });
    }

    function init() {
        document.addEventListener('click', handleNavClick);
        toggleConditionalFields(document);
        toggleDeudaFields(document);
        toggleFrecuenciaFields(document);
        initPendingAmountAutofill();
        initModules();
        if (window.location.hash) {
            var initialButtons = document.querySelectorAll('.gc-dashboard-button[href="' + window.location.hash + '"]');
            initialButtons.forEach(function (initial) {
                setActiveNav(initial);
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
