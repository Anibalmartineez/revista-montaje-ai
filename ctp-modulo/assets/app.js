(function () {
    const initOrderForm = () => {
        const container = document.querySelector('[data-ctp-items]');
        if (!container) {
            return;
        }

        const addButton = document.querySelector('.ctp-add-item');
        const totalGeneralEl = document.querySelector('[data-ctp-total-general]');

        const updateRowTotal = (row) => {
            const cantidadInput = row.querySelector('.ctp-cantidad');
            const precioInput = row.querySelector('.ctp-precio');
            const totalInput = row.querySelector('.ctp-total');

            const cantidad = parseFloat(cantidadInput?.value || 0);
            const precio = parseFloat(precioInput?.value || 0);
            const total = cantidad * precio;

            if (totalInput) {
                totalInput.value = total ? total.toFixed(2) : '';
            }
        };

        const updateGeneralTotal = () => {
            if (!totalGeneralEl) {
                return;
            }
            let total = 0;
            container.querySelectorAll('.ctp-total').forEach((input) => {
                const value = parseFloat(input.value || 0);
                total += value || 0;
            });
            totalGeneralEl.textContent = total.toFixed(2);
        };

        const handleMedidaToggle = (row) => {
            const select = row.querySelector('.ctp-medida');
            const otherInput = row.querySelector('.ctp-medida-otro');
            if (!select || !otherInput) {
                return;
            }
            if (select.value === 'otra') {
                otherInput.style.display = 'block';
                otherInput.required = true;
            } else {
                otherInput.style.display = 'none';
                otherInput.required = false;
                otherInput.value = '';
            }
        };

        const bindRow = (row) => {
            row.querySelectorAll('.ctp-cantidad, .ctp-precio').forEach((input) => {
                input.addEventListener('input', () => {
                    updateRowTotal(row);
                    updateGeneralTotal();
                });
            });

            const select = row.querySelector('.ctp-medida');
            if (select) {
                select.addEventListener('change', () => {
                    handleMedidaToggle(row);
                });
                handleMedidaToggle(row);
            }
        };

        container.querySelectorAll('[data-ctp-item]').forEach((row) => bindRow(row));

        if (addButton) {
            addButton.addEventListener('click', () => {
                const row = container.querySelector('[data-ctp-item]');
                if (!row) {
                    return;
                }
                const clone = row.cloneNode(true);
                clone.querySelectorAll('input').forEach((input) => {
                    if (input.type === 'number' || input.type === 'text') {
                        input.value = '';
                    }
                });
                clone.querySelectorAll('select').forEach((select) => {
                    select.selectedIndex = 0;
                });
                container.appendChild(clone);
                bindRow(clone);
                updateGeneralTotal();
            });
        }
    };

    const initLiquidaciones = () => {
        const totalEl = document.querySelector('[data-ctp-total-liquidacion]');
        if (!totalEl) {
            return;
        }
        const checkboxes = document.querySelectorAll('.ctp-liq-check');
        const update = () => {
            let total = 0;
            checkboxes.forEach((checkbox) => {
                if (!checkbox.checked) {
                    return;
                }
                const row = checkbox.closest('tr');
                const totalCell = row ? row.querySelector('td:last-child') : null;
                if (totalCell) {
                    const value = parseFloat(totalCell.textContent.replace(/\./g, '').replace(',', '.'));
                    if (!Number.isNaN(value)) {
                        total += value;
                    }
                }
            });
            totalEl.textContent = total.toFixed(2);
        };

        checkboxes.forEach((checkbox) => {
            checkbox.addEventListener('change', update);
        });
    };

    document.addEventListener('DOMContentLoaded', () => {
        initOrderForm();
        initLiquidaciones();
    });
})();
