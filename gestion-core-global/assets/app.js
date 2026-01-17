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

    function init() {
        document.addEventListener('click', handleNavClick);
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
