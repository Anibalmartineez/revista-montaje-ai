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
    const machineSelect = form.querySelector('[data-machine-select]');
    const horasInput = form.querySelector('[data-horas-input]');
    const costoInput = form.querySelector('[data-costo-input]');
    const clienteSelect = form.querySelector('[data-cliente-select]');
    const clienteTextWrapper = form.querySelector('[data-cliente-text]');
    const presupuestoIdInput = form.querySelector('[data-presupuesto-id]');

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
        alertBox.classList.toggle('is-warning', type === 'warning');
    };

    const clearAlert = () => {
        if (!alertBox) {
            return;
        }
        alertBox.textContent = '';
        alertBox.hidden = true;
        alertBox.classList.remove('is-success');
        alertBox.classList.remove('is-warning');
    };

    const parseNumber = (value) => {
        const parsed = parseFloat(value);
        return Number.isNaN(parsed) ? 0 : parsed;
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

    const updateClienteFields = () => {
        if (!clienteSelect || !clienteTextWrapper) {
            return;
        }
        const showOther = clienteSelect.value === 'other';
        clienteTextWrapper.hidden = !showOther;
        if (!showOther) {
            const input = clienteTextWrapper.querySelector('input');
            if (input) {
                input.value = '';
            }
        }
    };

    const getSelectedClienteId = () => {
        if (!clienteSelect) {
            return 0;
        }
        const value = clienteSelect.value;
        if (value === 'other' || value === '0' || value === '') {
            return 0;
        }
        const parsed = parseNumber(value);
        return parsed > 0 ? parsed : 0;
    };

    const updateCoreButtonState = () => {
        if (!coreButton) {
            return;
        }
        const hasCliente = getSelectedClienteId() > 0;
        coreButton.disabled = !config.coreAvailable || !hasCliente;
        if (!config.coreAvailable) {
            coreButton.title = config.strings.coreUnavailable || 'Core Global no disponible';
        } else if (!hasCliente) {
            coreButton.title = config.strings.coreClientRequired || 'Selecciona un cliente';
        } else {
            coreButton.title = '';
        }
    };

    const getPliegosEstimados = () => {
        const cantidad = parseNumber(form.querySelector('[name="cantidad"]')?.value);
        const formas = parseNumber(form.querySelector('[name="formas_por_pliego"]')?.value);
        const merma = parseNumber(form.querySelector('[name="merma_pct"]')?.value);
        if (!cantidad || !formas) {
            return 0;
        }
        return Math.ceil((cantidad / Math.max(1, formas)) * (1 + merma / 100));
    };

    const updateMachineFields = () => {
        if (!machineSelect) {
            return;
        }
        const selected = machineSelect.options[machineSelect.selectedIndex];
        const cost = selected ? parseNumber(selected.dataset.cost) : 0;
        const rendimiento = selected ? parseNumber(selected.dataset.rendimiento) : 0;

        if (costoInput && (!costoInput.value || costoInput.dataset.userEdited !== 'true')) {
            costoInput.value = cost ? cost.toFixed(2) : '';
        }

        if (horasInput && horasInput.dataset.userEdited !== 'true' && rendimiento > 0) {
            const pliegos = getPliegosEstimados();
            if (pliegos > 0) {
                horasInput.value = (pliegos / rendimiento).toFixed(2);
            }
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
        if (horasInput && typeof data.horas_maquina === 'number' && horasInput.dataset.userEdited !== 'true') {
            horasInput.value = data.horas_maquina ? parseNumber(data.horas_maquina).toFixed(2) : '';
        }
        if (costoInput && typeof data.costo_hora === 'number' && costoInput.dataset.userEdited !== 'true') {
            costoInput.value = data.costo_hora ? parseNumber(data.costo_hora).toFixed(2) : '';
        }
        if (machineSelect && data.maquina_id && parseNumber(machineSelect.value) === 0) {
            machineSelect.value = String(data.maquina_id);
        }
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
        if (payload.data?.price_note) {
            showAlert(payload.data.price_note, 'warning');
        }
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
        if (presupuestoIdInput && payload.data?.id) {
            presupuestoIdInput.value = payload.data.id;
        }
        updateCoreButtonState();
    };

    const createCoreDocument = async () => {
        if (!config.coreAvailable) {
            showAlert(config.strings.coreUnavailable || 'Core Global no disponible');
            return;
        }
        if (getSelectedClienteId() <= 0) {
            showAlert(config.strings.coreClientRequired || 'Selecciona un cliente de Core.', 'warning');
            return;
        }
        if (!presupuestoIdInput || !presupuestoIdInput.value) {
            showAlert(config.strings.coreSaveRequired || 'Guarda el presupuesto antes de crear el documento.', 'warning');
            return;
        }
        clearAlert();
        const formData = getFormData();
        formData.append('action', 'cpo_offset_create_core_document');

        const response = await fetch(config.ajaxUrl, {
            method: 'POST',
            credentials: 'same-origin',
            body: formData,
        });

        const payload = await response.json();
        if (!payload.success) {
            showAlert(payload.data?.message || 'Error');
            return;
        }
        showAlert(payload.data?.message || config.strings.coreCreated, 'success');
    };

    calcButton?.addEventListener('click', () => {
        calculate();
    });

    saveButton?.addEventListener('click', () => {
        savePresupuesto();
    });
    coreButton?.addEventListener('click', () => {
        createCoreDocument();
    });

    materialSelect?.addEventListener('change', updateMaterialPrice);
    clienteSelect?.addEventListener('change', () => {
        updateClienteFields();
        updateCoreButtonState();
    });
    pliegoSelect?.addEventListener('change', () => {
        toggleCustomPliego();
        updateMachineFields();
    });
    machineSelect?.addEventListener('change', updateMachineFields);

    horasInput?.addEventListener('input', () => {
        horasInput.dataset.userEdited = 'true';
    });
    costoInput?.addEventListener('input', () => {
        costoInput.dataset.userEdited = 'true';
    });

    updateMaterialPrice();
    toggleCustomPliego();
    updateMachineFields();
    updateClienteFields();

    if (coreButton) {
        updateCoreButtonState();
    }
})();
