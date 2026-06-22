from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_frontend_files_exist():
    assert (ROOT / "frontend/templates/presupuesto_offset_app.html").exists()
    assert (ROOT / "frontend/static/css/presupuesto_offset.css").exists()
    assert (ROOT / "frontend/static/js/presupuesto_offset.js").exists()


def test_html_has_main_containers():
    html = read("frontend/templates/presupuesto_offset_app.html")

    assert 'id="sp-quote-form"' in html
    assert "Calcular presupuesto" in html
    assert 'id="sp-precio-final"' in html
    assert 'id="sp-budget-list"' in html
    assert 'id="sp-json-output"' in html
    assert 'id="sp-catalogs-section"' in html
    assert 'id="sp-catalog-type"' in html
    assert 'id="sp-clients-section"' in html
    assert 'id="sp-client-list"' in html


def test_css_uses_isolated_prefix():
    css = read("frontend/static/css/presupuesto_offset.css")

    assert ".sp-shell" in css
    assert ".sp-panel" in css
    assert "editor_offset" not in css
    assert "editor-offset" not in css


def test_js_uses_api_and_does_not_reference_editor():
    js = read("frontend/static/js/presupuesto_offset.js")

    assert "/api/sistema-presupuesto" in js
    assert "/custom" in js
    assert "sp-catalog-list" in js
    assert "/clientes" in js
    assert "sp-client-list" in js
    assert "editor_offset" not in js
    assert "editor-offset" not in js
    assert "/editor_offset" not in js


def test_dev_app_supports_configurable_data_dir():
    source = read("dev_app.py")

    assert "SISTEMA_PRESUPUESTO_DATA_DIR" in source
    assert "os.environ.get" in source
