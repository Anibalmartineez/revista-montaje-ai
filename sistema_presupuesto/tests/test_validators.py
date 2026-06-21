import copy
import json
from pathlib import Path

import pytest

from sistema_presupuesto.backend.validators import (
    catalog_refs_from_catalogs,
    validate_quote_request,
    validate_quote_request_or_raise,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


@pytest.fixture()
def catalog_refs():
    return catalog_refs_from_catalogs(
        materiales_catalog=load_json("data/catalogo/materiales_default.json"),
        maquinas_catalog=load_json("data/catalogo/maquinas_default.json"),
        procesos_catalog=load_json("data/catalogo/procesos_default.json"),
    )


@pytest.mark.parametrize(
    "fixture_path",
    [
        "data/fixtures/quote_request_volante.json",
        "data/fixtures/quote_request_tarjeta.json",
        "data/fixtures/quote_request_revista.json",
        "data/fixtures/quote_request_diptico.json",
        "data/fixtures/quote_request_triptico.json",
    ],
)
def test_phase_2_quote_request_fixtures_are_valid(fixture_path, catalog_refs):
    payload = load_json(fixture_path)

    report = validate_quote_request(payload, catalog_refs)

    assert report.to_dict()["errors"] == []
    assert report.ok is True


def test_negative_quantity_fails(catalog_refs):
    payload = load_json("data/fixtures/quote_request_volante.json")
    payload["producto"]["cantidad"] = "-1"

    report = validate_quote_request(payload, catalog_refs)

    assert not report.ok
    assert any(error.code == "NON_POSITIVE_NUMBER" for error in report.errors)


def test_invalid_currency_fails(catalog_refs):
    payload = load_json("data/fixtures/quote_request_volante.json")
    payload["costos"]["moneda"] = "USD"

    report = validate_quote_request(payload, catalog_refs)

    assert not report.ok
    assert any(error.code == "INVALID_CURRENCY" for error in report.errors)


def test_zero_measure_fails(catalog_refs):
    payload = load_json("data/fixtures/quote_request_volante.json")
    payload["producto"]["ancho_mm"] = "0"

    report = validate_quote_request(payload, catalog_refs)

    assert not report.ok
    assert any(error.path == "producto.ancho_mm" for error in report.errors)


def test_unknown_material_fails(catalog_refs):
    payload = load_json("data/fixtures/quote_request_volante.json")
    payload["costos"]["material_id"] = "material_inexistente"

    report = validate_quote_request(payload, catalog_refs)

    assert not report.ok
    assert any(error.code == "UNKNOWN_MATERIAL" for error in report.errors)


def test_unknown_machine_fails(catalog_refs):
    payload = load_json("data/fixtures/quote_request_volante.json")
    payload["costos"]["maquina_id"] = "maquina_inexistente"

    report = validate_quote_request(payload, catalog_refs)

    assert not report.ok
    assert any(error.code == "UNKNOWN_MACHINE" for error in report.errors)


def test_revista_pages_must_be_multiple_of_four(catalog_refs):
    payload = load_json("data/fixtures/quote_request_revista.json")
    payload["producto"]["paginas"] = 30

    report = validate_quote_request(payload, catalog_refs)

    assert not report.ok
    assert any(error.code == "INVALID_PAGE_MULTIPLE" for error in report.errors)


def test_margin_and_markup_cannot_be_active_together(catalog_refs):
    payload = load_json("data/fixtures/quote_request_volante.json")
    payload["costos"]["markup_pct"] = "20"

    report = validate_quote_request(payload, catalog_refs)

    assert not report.ok
    assert any(error.code == "MARGIN_AND_MARKUP" for error in report.errors)


def test_validate_or_raise_returns_model(catalog_refs):
    payload = load_json("data/fixtures/quote_request_volante.json")

    model = validate_quote_request_or_raise(payload, catalog_refs)

    assert model.producto.tipo == "volante"
    assert str(model.producto.cantidad) == "1000"


def test_float_money_or_measure_is_rejected(catalog_refs):
    payload = copy.deepcopy(load_json("data/fixtures/quote_request_volante.json"))
    payload["costos"]["margen_pct"] = 30.0

    report = validate_quote_request(payload, catalog_refs)

    assert not report.ok
    assert any(error.code == "FLOAT_NOT_ALLOWED" for error in report.errors)
