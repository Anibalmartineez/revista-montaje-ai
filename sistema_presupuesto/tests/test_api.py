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


def valid_material(**overrides):
    item = {
        "id": "material_api_test",
        "nombre": "Material API test",
        "tipo": "papel_test",
        "gramaje_g_m2": "1",
        "formato_pliego_mm": {"ancho": "1", "alto": "1"},
        "costo": {
            "modo": "por_pliego",
            "moneda": "PYG",
            "valor": "0",
            "unidad": "pliego",
            "es_valor_ejemplo": True,
        },
        "merma_recomendada_pct": "0",
        "activo": True,
    }
    item.update(overrides)
    return item


def valid_client(**overrides):
    payload = {
        "nombre": "Cliente API",
        "empresa": "Empresa API",
        "telefono": "0981000000",
        "email": "cliente.api@example.com",
        "ruc": "1234567-8",
        "notas": "Cliente creado por test API.",
    }
    payload.update(overrides)
    return payload


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


def test_custom_catalog_api_crud(client):
    create_response = client.post(
        "/api/sistema-presupuesto/catalogos/materiales/custom",
        json=valid_material(),
    )
    assert create_response.status_code == 201
    assert create_response.get_json()["item"]["id"] == "material_api_test"

    custom_response = client.get("/api/sistema-presupuesto/catalogos/materiales/custom")
    assert custom_response.status_code == 200
    assert custom_response.get_json()["catalogo"]["materiales"][0]["id"] == "material_api_test"

    combined_response = client.get("/api/sistema-presupuesto/catalogos/materiales")
    assert combined_response.status_code == 200
    combined_items = combined_response.get_json()["catalogo"]["materiales"]
    assert any(item["id"] == "material_api_test" and item["origen_catalogo"] == "custom" for item in combined_items)

    update_response = client.put(
        "/api/sistema-presupuesto/catalogos/materiales/custom/material_api_test",
        json={"nombre": "Material API actualizado"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["nombre"] == "Material API actualizado"

    delete_response = client.delete("/api/sistema-presupuesto/catalogos/materiales/custom/material_api_test")
    assert delete_response.status_code == 200
    assert delete_response.get_json()["deleted"] is True


def test_custom_catalog_api_rejects_invalid_item(client):
    response = client.post(
        "/api/sistema-presupuesto/catalogos/materiales/custom",
        json={"id": "material_invalido"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "REPOSITORY_ERROR"


def test_custom_catalog_api_override_is_used_by_legacy_endpoint(client):
    response = client.post(
        "/api/sistema-presupuesto/catalogos/materiales/custom",
        json=valid_material(id="couche_150", nombre="Papel override API"),
    )
    assert response.status_code == 201

    legacy_response = client.get("/api/sistema-presupuesto/catalogos/materiales")
    items = legacy_response.get_json()["catalogo"]["materiales"]
    matches = [item for item in items if item["id"] == "couche_150"]

    assert legacy_response.status_code == 200
    assert len(matches) == 1
    assert matches[0]["nombre"] == "Papel override API"
    assert matches[0]["origen_catalogo"] == "custom"


def test_client_api_crud(client):
    create_response = client.post("/api/sistema-presupuesto/clientes", json=valid_client())
    assert create_response.status_code == 201
    created = create_response.get_json()["cliente"]
    cliente_id = created["cliente_id"]
    assert created["nombre"] == "Cliente API"

    list_response = client.get("/api/sistema-presupuesto/clientes")
    assert list_response.status_code == 200
    assert list_response.get_json()["clientes"][0]["cliente_id"] == cliente_id

    get_response = client.get(f"/api/sistema-presupuesto/clientes/{cliente_id}")
    assert get_response.status_code == 200
    assert get_response.get_json()["cliente"]["cliente_id"] == cliente_id

    update_response = client.put(
        f"/api/sistema-presupuesto/clientes/{cliente_id}",
        json={"nombre": "Cliente API Actualizado", "email": ""},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["cliente"]["nombre"] == "Cliente API Actualizado"

    delete_response = client.delete(f"/api/sistema-presupuesto/clientes/{cliente_id}")
    assert delete_response.status_code == 200
    assert delete_response.get_json()["deleted"] is True


def test_client_api_rejects_missing_name(client):
    response = client.post("/api/sistema-presupuesto/clientes", json=valid_client(nombre=""))

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "REPOSITORY_ERROR"


def test_client_api_rejects_invalid_email(client):
    response = client.post("/api/sistema-presupuesto/clientes", json=valid_client(email="email-invalido"))

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "REPOSITORY_ERROR"


def test_missing_client_returns_controlled_error(client):
    response = client.get("/api/sistema-presupuesto/clientes/cli_20260622_abcdef123456")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "JSON_NOT_FOUND"


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
    numero_comercial = saved["numero_comercial"]
    assert numero_comercial.startswith("PRES-")
    assert saved["record"]["numero_comercial"] == numero_comercial

    list_response = client.get("/api/sistema-presupuesto/presupuestos")
    assert list_response.status_code == 200
    listed = list_response.get_json()
    assert listed["presupuestos"][0]["presupuesto_id"] == presupuesto_id
    assert listed["presupuestos"][0]["numero_comercial"] == numero_comercial

    get_response = client.get(f"/api/sistema-presupuesto/presupuestos/{presupuesto_id}")
    assert get_response.status_code == 200
    viewed = get_response.get_json()
    assert viewed["record"]["presupuesto_id"] == presupuesto_id
    assert viewed["record"]["numero_comercial"] == numero_comercial


def test_generate_budget_document_endpoint_and_download(client):
    quote_request = load_json("data/fixtures/quote_request_volante.json")
    save_response = client.post("/api/sistema-presupuesto/cotizar-y-guardar", json=quote_request)
    presupuesto_id = save_response.get_json()["presupuesto_id"]

    document_response = client.post(f"/api/sistema-presupuesto/presupuestos/{presupuesto_id}/documento")

    assert document_response.status_code == 200
    payload = document_response.get_json()
    assert payload["ok"] is True
    assert payload["presupuesto_id"] == presupuesto_id
    assert payload["numero_comercial"].startswith("PRES-")
    assert payload["tipo_documento"] in {"pdf", "html"}
    assert payload["ruta_relativa"].startswith("pdfs/")

    download_response = client.get(f"/api/sistema-presupuesto/documentos/{payload['archivo']}")
    assert download_response.status_code == 200
    assert download_response.data


def test_document_download_rejects_path_traversal_like_filename(client):
    response = client.get("/api/sistema-presupuesto/documentos/..secret.pdf")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "REPOSITORY_ERROR"


def test_numbering_status_endpoint_does_not_increment(client):
    first_response = client.get("/api/sistema-presupuesto/numeracion")
    second_response = client.get("/api/sistema-presupuesto/numeracion")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = first_response.get_json()["numeracion"]
    second = second_response.get_json()["numeracion"]
    assert first["last_number"] == 0
    assert first["next_number_preview"].endswith("000001")
    assert second["last_number"] == 0


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
