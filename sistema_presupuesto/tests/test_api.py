import json
from pathlib import Path

import pytest
from flask import Flask

from sistema_presupuesto.api import presupuesto_api_bp

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def copy_catalogs(tmp_path):
    catalog_dir = tmp_path / "catalogo"
    catalog_dir.mkdir(parents=True)
    for source in (ROOT / "data" / "catalogo").glob("*.json"):
        (catalog_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


@pytest.fixture()
def app(tmp_path):
    copy_catalogs(tmp_path)
    test_app = Flask(__name__)
    test_app.config["TESTING"] = True
    test_app.config["SISTEMA_PRESUPUESTO_DATA_DIR"] = str(tmp_path)
    test_app.register_blueprint(presupuesto_api_bp)
    return test_app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_health_responds_ok(client):
    response = client.get("/api/sistema-presupuesto/health")

    assert response.status_code == 200
    assert response.get_json()["ok"] is True


@pytest.mark.parametrize(
    "endpoint,collection_key",
    [
        ("/api/sistema-presupuesto/catalogos/materiales", "materiales"),
        ("/api/sistema-presupuesto/catalogos/maquinas", "maquinas"),
        ("/api/sistema-presupuesto/catalogos/procesos", "procesos"),
    ],
)
def test_catalog_endpoints_return_json(client, endpoint, collection_key):
    response = client.get(endpoint)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["catalogo"][collection_key]


def test_cotizar_calculates_valid_fixture(client):
    quote_request = load_json("data/fixtures/quote_request_volante.json")

    response = client.post("/api/sistema-presupuesto/cotizar", json=quote_request)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["result"]["request_fixture_id"] == "quote_request_volante"
    assert payload["result"]["warnings"]


def test_cotizar_fails_with_invalid_contract(client):
    quote_request = load_json("data/fixtures/quote_request_volante.json")
    quote_request["producto"]["cantidad"] = "-1"

    response = client.post("/api/sistema-presupuesto/cotizar", json=quote_request)

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "CONTRACT_INVALID"
    assert any(error["code"] == "NON_POSITIVE_NUMBER" for error in payload["validation"]["errors"])


def test_cotizar_fails_with_invalid_json(client):
    response = client.post(
        "/api/sistema-presupuesto/cotizar",
        data="{bad json",
        content_type="application/json",
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_JSON"


def test_cotizar_y_guardar_then_list_and_get(client):
    quote_request = load_json("data/fixtures/quote_request_volante.json")

    save_response = client.post("/api/sistema-presupuesto/cotizar-y-guardar", json=quote_request)

    assert save_response.status_code == 201
    saved = save_response.get_json()
    presupuesto_id = saved["presupuesto_id"]

    list_response = client.get("/api/sistema-presupuesto/presupuestos")
    assert list_response.status_code == 200
    listed = list_response.get_json()
    assert listed["presupuestos"][0]["presupuesto_id"] == presupuesto_id

    get_response = client.get(f"/api/sistema-presupuesto/presupuestos/{presupuesto_id}")
    assert get_response.status_code == 200
    viewed = get_response.get_json()
    assert viewed["record"]["presupuesto_id"] == presupuesto_id


def test_missing_budget_returns_controlled_error(client):
    response = client.get("/api/sistema-presupuesto/presupuestos/psp_20260621_abcdef123456")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "JSON_NOT_FOUND"


def test_missing_catalog_returns_controlled_error(tmp_path):
    test_app = Flask(__name__)
    test_app.config["TESTING"] = True
    test_app.config["SISTEMA_PRESUPUESTO_DATA_DIR"] = str(tmp_path)
    test_app.register_blueprint(presupuesto_api_bp)
    client = test_app.test_client()

    response = client.get("/api/sistema-presupuesto/catalogos/materiales")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "JSON_NOT_FOUND"
