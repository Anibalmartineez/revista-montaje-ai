(function () {
    const form = document.querySelector('[data-cpo-presupuesto]');
    if (!form || typeof window.cpoOffsetPresupuesto === 'undefined') {
        return;
    }

    const config = window.cpoOffsetPresupuesto;
    const calcButton = form.querySelector('[data-cpo-calc]');
    const saveButton = form.querySelector('[data-cpo-save]');
    const coreButton = form.querySelector('[data-cpo-core]');
    const alertBox = form.querySelector('[data-cpo-alert]');
    const materialSelect = form.querySelector('[data-material-select]');
    const materialPrice = form.querySelector('[data-material-price]');
    const pliegoSelect = form.querySelector('[data-pliego-select]');
    const pliegoCustom = form.querySelector('[data-pliego-custom]');

    const formatCurrency = (value) => {
        if (Number.isNaN(value)) {
            return '-';
        }
        return new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
    };

    const showAlert = (message, type = 'error') => {
        if (!alertBox) {
            return;
        }
        alertBox.textContent = message;
        alertBox.hidden = false;
        alertBox.classList.toggle('is-success', type === 'success');
    };

    const clearAlert = () => {
        if (!alertBox) {
            return;
        }
        alertBox.textContent = '';
        alertBox.hidden = true;
        alertBox.classList.remove('is-success');
    };

    const updateMaterialPrice = () => {
        if (!materialSelect || !materialPrice) {
            return;
        }
        const selected = materialSelect.options[materialSelect.selectedIndex];
        const price = selected ? selected.dataset.price : '';
        const currency = selected ? selected.dataset.moneda : 'PYG';
        if (price) {
            materialPrice.textContent = `Precio vigente: ${formatCurrency(parseFloat(price))} ${currency}`;
        } else {
            materialPrice.textContent = config.strings.priceMissing;
        }
    };

    const toggleCustomPliego = () => {
        if (!pliegoSelect || !pliegoCustom) {
            return;
        }
        const isCustom = pliegoSelect.value === 'custom';
        pliegoCustom.hidden = !isCustom;
    };

    const getFormData = () => {
        const formData = new FormData(form);
        formData.append('nonce', config.nonce);
        return formData;
    };

    const applyResults = (data) => {
        const results = form.querySelectorAll('[data-result]');
        results.forEach((node) => {
            const key = node.dataset.result;
            if (!key) {
                return;
            }
            if (key === 'price_note') {
                node.textContent = data.price_note || '';
                return;
            }
            const value = data[key];
            if (key === 'pliegos_necesarios') {
                node.textContent = value ?? '-';
            } else if (typeof value === 'number') {
                node.textContent = formatCurrency(value);
            } else {
                node.textContent = value ?? '-';
            }
        });
    };

    const calculate = async () => {
        clearAlert();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_calculate');

        const response = await fetch(config.ajaxUrl, {
            method: 'POST',
            credentials: 'same-origin',
            body: formData,
        });

        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || 'Error');
            return null;
        }
        applyResults(payload.data);
        return payload.data;
    };

    const savePresupuesto = async () => {
        if (!config.canSave) {
            showAlert('Debes iniciar sesión para guardar.');
            return;
        }
        clearAlert();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_save_presupuesto');

        const response = await fetch(config.ajaxUrl, {
            method: 'POST',
            credentials: 'same-origin',
            body: formData,
        });

        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || config.strings.savingError);
            return;
        }
        showAlert(payload.data?.message || config.strings.saved, 'success');
    };

    calcButton?.addEventListener('click', () => {
        calculate();
    });

    saveButton?.addEventListener('click', () => {
        savePresupuesto();
    });

    materialSelect?.addEventListener('change', updateMaterialPrice);
    pliegoSelect?.addEventListener('change', toggleCustomPliego);

    updateMaterialPrice();
    toggleCustomPliego();

    if (coreButton) {
        coreButton.disabled = !config.coreAvailable;
        if (!config.coreAvailable) {
            coreButton.title = 'Core Global no disponible';
        }
    }
})();
