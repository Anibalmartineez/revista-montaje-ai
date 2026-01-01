(function () {
    function updateTotal(form) {
        var quantityInput = form.querySelector('.ctp-quantity');
        var priceInput = form.querySelector('.ctp-price');
        var totalInput = form.querySelector('.ctp-total');

        if (!quantityInput || !priceInput || !totalInput) {
            return;
        }

        var quantity = parseInt(quantityInput.value, 10);
        var price = parseFloat(priceInput.value);

        if (isNaN(quantity) || quantity < 1) {
            quantity = 1;
        }
        if (isNaN(price) || price < 0) {
            price = 0;
        }

        var total = quantity * price;
        totalInput.value = total.toFixed(2);
    }

    document.addEventListener('input', function (event) {
        var target = event.target;
        if (!target.classList.contains('ctp-quantity') && !target.classList.contains('ctp-price')) {
            return;
        }

        var form = target.closest('.ctp-form');
        if (form) {
            updateTotal(form);
        }
    });

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.ctp-form').forEach(function (form) {
            updateTotal(form);
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
