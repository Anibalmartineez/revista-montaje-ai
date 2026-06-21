import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from sistema_presupuesto.backend.calculation_engine import calculate_quote_from_dict
from sistema_presupuesto.backend.errors import ContractValidationError
from sistema_presupuesto.backend.serializers import quote_result_to_dict

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


@pytest.fixture()
def catalogs():
    return {
        "materiales_catalog": load_json("data/catalogo/materiales_default.json"),
        "maquinas_catalog": load_json("data/catalogo/maquinas_default.json"),
        "procesos_catalog": load_json("data/catalogo/procesos_default.json"),
    }


@pytest.mark.parametrize(
    "fixture_name",
    [
        "quote_request_volante",
        "quote_request_tarjeta",
        "quote_request_revista",
        "quote_request_diptico",
        "quote_request_triptico",
    ],
)
def test_all_valid_fixtures_calculate_without_error(fixture_name, catalogs):
    payload = load_json(f"data/fixtures/{fixture_name}.json")

    result = calculate_quote_from_dict(payload, **catalogs)

    assert result.ok
    assert result.costos.costo_tecnico > Decimal("0")
    assert result.costos.precio_final > Decimal("0")
    assert result.warnings


def test_volante_generates_full_auditable_breakdown(catalogs):
    payload = load_json("data/fixtures/quote_request_volante.json")

    result = calculate_quote_from_dict(payload, **catalogs)
    result_dict = quote_result_to_dict(result)

    codes = {item["codigo"] for item in result_dict["costos"]["items"]}
    assert {"papel", "chapas_ctp", "maquina"}.issubset(codes)
    assert result_dict["produccion"]["unidades_por_pliego"] == "16"
    assert result_dict["produccion"]["pliegos_buenos"] == "63"
    assert result_dict["produccion"]["chapas"] == "4"


def test_folded_products_calculate_as_open_format(catalogs):
    diptico = calculate_quote_from_dict(load_json("data/fixtures/quote_request_diptico.json"), **catalogs)
    triptico = calculate_quote_from_dict(load_json("data/fixtures/quote_request_triptico.json"), **catalogs)

    assert diptico.produccion.pieza_con_sangrado_mm.ancho == Decimal("303")
    assert triptico.produccion.pieza_con_sangrado_mm.ancho == Decimal("303")
    assert diptico.produccion.unidades_por_pliego == triptico.produccion.unidades_por_pliego


def test_price_unit_reconciles_with_final_price(catalogs):
    payload = load_json("data/fixtures/quote_request_tarjeta.json")

    result = calculate_quote_from_dict(payload, **catalogs)

    assert result.costos.precio_unitario == result.costos.precio_final / Decimal("500")


def test_invalid_input_still_fails_before_calculation(catalogs):
    payload = copy.deepcopy(load_json("data/fixtures/quote_request_volante.json"))
    payload["producto"]["cantidad"] = "-10"

    with pytest.raises(ContractValidationError) as exc_info:
        calculate_quote_from_dict(payload, **catalogs)

    assert any(error.code == "NON_POSITIVE_NUMBER" for error in exc_info.value.report.errors)

