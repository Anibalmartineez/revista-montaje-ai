(function () {
    function normalizeNumber(value, fallback) {
        var parsed = parseFloat(value);
        if (isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function updateOrderTotals(form) {
        if (!form) {
            return;
        }

        var rows = form.querySelectorAll('[data-ctp-item]');
        var totalOrder = 0;

        rows.forEach(function (row) {
            var quantityInput = row.querySelector('.ctp-item-quantity');
            var priceInput = row.querySelector('.ctp-item-price');
            var totalInput = row.querySelector('.ctp-item-total');

            if (!quantityInput || !priceInput || !totalInput) {
                return;
            }

            var quantity = parseInt(quantityInput.value, 10);
            if (isNaN(quantity) || quantity < 1) {
                quantity = 1;
            }

            var price = normalizeNumber(priceInput.value, 0);
            if (price < 0) {
                price = 0;
            }

            var total = quantity * price;
            totalInput.value = total.toFixed(2);
            totalOrder += total;
        });

        var orderTotalInput = form.querySelector('.ctp-order-total');
        if (orderTotalInput) {
            orderTotalInput.value = totalOrder.toFixed(2);
        }
    }

    function syncRemoveButtons(container) {
        if (!container) {
            return;
        }

        var rows = container.querySelectorAll('[data-ctp-item]');
        var disableRemove = rows.length <= 1;
        rows.forEach(function (row) {
            var removeButton = row.querySelector('.ctp-remove-item');
            if (removeButton) {
                removeButton.disabled = disableRemove;
            }
        });
    }

    document.addEventListener('input', function (event) {
        var target = event.target;
        if (!target.classList.contains('ctp-item-quantity') && !target.classList.contains('ctp-item-price')) {
            return;
        }

        var form = target.closest('.ctp-order-form');
        if (form) {
            updateOrderTotals(form);
        }
    });

    document.addEventListener('click', function (event) {
        var target = event.target;
        if (target.classList.contains('ctp-add-item')) {
            var form = target.closest('.ctp-order-form');
            if (!form) {
                return;
            }

            var container = form.querySelector('[data-ctp-items]');
            var template = form.querySelector('.ctp-order-item-template');
            if (!container || !template || !template.content) {
                return;
            }

            container.appendChild(template.content.cloneNode(true));
            syncRemoveButtons(container);
            updateOrderTotals(form);
        }

        if (target.classList.contains('ctp-remove-item')) {
            var row = target.closest('[data-ctp-item]');
            if (!row) {
                return;
            }
            var itemsContainer = row.closest('[data-ctp-items]');
            if (!itemsContainer) {
                return;
            }

            var rows = itemsContainer.querySelectorAll('[data-ctp-item]');
            if (rows.length <= 1) {
                return;
            }

            row.remove();
            syncRemoveButtons(itemsContainer);
            var parentForm = itemsContainer.closest('.ctp-order-form');
            updateOrderTotals(parentForm);
        }
    });

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.ctp-order-form').forEach(function (form) {
            updateOrderTotals(form);
            var container = form.querySelector('[data-ctp-items]');
            syncRemoveButtons(container);
        });

        document.querySelectorAll('.ctp-client-select').forEach(function (select) {
            var form = select.closest('.ctp-form');
            if (!form) {
                return;
            }
            var nameInput = form.querySelector('.ctp-client-name');
            if (!nameInput) {
                return;
            }

            var syncName = function () {
                var selectedOption = select.options[select.selectedIndex];
                if (!selectedOption) {
                    return;
                }
                if (select.value && select.value !== '0') {
                    nameInput.value = selectedOption.textContent.trim();
                    nameInput.readOnly = true;
                } else {
                    nameInput.readOnly = false;
                }
            };

            select.addEventListener('change', syncName);
            syncName();
        });

        document.querySelectorAll('.ctp-client-search').forEach(function (input) {
            var targetId = input.getAttribute('data-target');
            if (!targetId) {
                return;
            }
            var select = document.getElementById(targetId);
            if (!select) {
                return;
            }

            input.addEventListener('input', function () {
                var term = input.value.toLowerCase();
                Array.prototype.slice.call(select.options).forEach(function (option) {
                    if (option.value === '0') {
                        option.hidden = false;
                        return;
                    }
                    if (!term) {
                        option.hidden = false;
                        return;
                    }
                    option.hidden = option.textContent.toLowerCase().indexOf(term) === -1;
                });
            });
        });

        document.querySelectorAll('.ctp-order-filter').forEach(function (form) {
            var fields = form.querySelector('.ctp-filter-fields');
            if (!fields) {
                return;
            }

            var updateMode = function () {
                var selected = form.querySelector('input[name="ctp_period"]:checked');
                if (selected) {
                    fields.setAttribute('data-mode', selected.value);
                }
            };

            form.addEventListener('change', function (event) {
                if (event.target && event.target.name === 'ctp_period') {
                    updateMode();
                }
            });

            updateMode();
        });
    });
})();
