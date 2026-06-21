import json
from decimal import Decimal
from pathlib import Path

from sistema_presupuesto.backend.production_math import estimate_production, piece_size_with_bleed
from sistema_presupuesto.backend.serializers import quote_request_from_dict

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def load_request(name):
    return quote_request_from_dict(load_json(f"data/fixtures/{name}.json"))


def machine():
    catalog = load_json("data/catalogo/maquinas_default.json")
    return catalog["maquinas"][0]


def test_piece_with_bleed_for_volante():
    request = load_request("quote_request_volante")

    size = piece_size_with_bleed(request)

    assert size.ancho == Decimal("154")
    assert size.alto == Decimal("216")


def test_tarjeta_units_per_sheet_matches_fixture_expectation():
    request = load_request("quote_request_tarjeta")

    estimate = estimate_production(request, machine())

    assert estimate.unidades_por_pliego == Decimal("119")
    assert estimate.pliegos_buenos == Decimal("5")


def test_merma_increases_gross_sheets():
    request = load_request("quote_request_volante")

    estimate = estimate_production(request, machine())

    assert estimate.pliegos_brutos > estimate.pliegos_buenos
    assert estimate.merma_pliegos > Decimal("0")


def test_revista_uses_page_factor_and_reasonable_plates():
    request = load_request("quote_request_revista")

    estimate = estimate_production(request, machine())

    assert estimate.factor_paginas == Decimal("8")
    assert estimate.chapas == Decimal("64")
    assert estimate.pasadas == Decimal("2")
    assert any(warning.code == "MAGAZINE_SIGNATURE_APPROXIMATION" for warning in estimate.warnings)

