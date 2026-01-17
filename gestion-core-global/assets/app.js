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

    function init() {
        document.addEventListener('click', handleNavClick);
        toggleConditionalFields(document);
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
