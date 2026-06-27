from pathlib import Path

from app import app as main_app
from sistema_presupuesto.dev_app import create_dev_app

ROOT = Path(__file__).resolve().parents[1]


def copy_catalogs(tmp_path):
    catalog_dir = tmp_path / "catalogo"
    catalog_dir.mkdir(parents=True)
    for source in (ROOT / "data" / "catalogo").glob("*.json"):
        (catalog_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def test_main_app_serves_sistema_presupuesto_ui_without_editor_dependency(tmp_path):
    copy_catalogs(tmp_path)
    previous_data_dir = main_app.config.get("SISTEMA_PRESUPUESTO_DATA_DIR")
    previous_testing = main_app.config.get("TESTING")
    main_app.config["TESTING"] = True
    main_app.config["SISTEMA_PRESUPUESTO_DATA_DIR"] = str(tmp_path)

    try:
        with main_app.test_client() as client:
            response = client.get("/sistema-presupuesto")
    finally:
        main_app.config["SISTEMA_PRESUPUESTO_DATA_DIR"] = previous_data_dir
        main_app.config["TESTING"] = previous_testing

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Sistema Presupuesto Offset" in html
    assert "/sistema-presupuesto/static/css/presupuesto_offset.css" in html
    assert "/sistema-presupuesto/static/js/presupuesto_offset.js" in html
    assert "INITIAL_LAYOUT_JSON" not in html
    assert "layout_constructor" not in html


def test_main_app_serves_isolated_budget_static_files():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        css_response = client.get("/sistema-presupuesto/static/css/presupuesto_offset.css")
        js_response = client.get("/sistema-presupuesto/static/js/presupuesto_offset.js")

    assert css_response.status_code == 200
    assert ".sp-shell" in css_response.get_data(as_text=True)
    assert js_response.status_code == 200
    assert "/api/sistema-presupuesto" in js_response.get_data(as_text=True)


def test_main_app_budget_api_endpoints_are_active(tmp_path):
    copy_catalogs(tmp_path)
    previous_data_dir = main_app.config.get("SISTEMA_PRESUPUESTO_DATA_DIR")
    previous_testing = main_app.config.get("TESTING")
    main_app.config["TESTING"] = True
    main_app.config["SISTEMA_PRESUPUESTO_DATA_DIR"] = str(tmp_path)

    try:
        with main_app.test_client() as client:
            health_response = client.get("/api/sistema-presupuesto/health")
            materials_response = client.get("/api/sistema-presupuesto/catalogos/materiales")
    finally:
        main_app.config["SISTEMA_PRESUPUESTO_DATA_DIR"] = previous_data_dir
        main_app.config["TESTING"] = previous_testing

    assert health_response.status_code == 200
    assert health_response.get_json()["ok"] is True
    assert materials_response.status_code == 200
    assert materials_response.get_json()["catalogo"]["materiales"]


def test_main_existing_index_route_still_responds():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Presupuesto Offset" in response.get_data(as_text=True)


def test_dev_app_still_serves_isolated_ui_and_api(tmp_path, monkeypatch):
    copy_catalogs(tmp_path)
    monkeypatch.setenv("SISTEMA_PRESUPUESTO_DATA_DIR", str(tmp_path))
    dev_app = create_dev_app()
    dev_app.config["TESTING"] = True

    with dev_app.test_client() as client:
        ui_response = client.get("/sistema-presupuesto-ui")
        static_response = client.get("/sistema-presupuesto-ui/static/js/presupuesto_offset.js")
        health_response = client.get("/api/sistema-presupuesto/health")

    html = ui_response.get_data(as_text=True)
    assert ui_response.status_code == 200
    assert "Sistema Presupuesto Offset" in html
    assert "/sistema-presupuesto-ui/static/js/presupuesto_offset.js" in html
    assert static_response.status_code == 200
    assert health_response.status_code == 200
