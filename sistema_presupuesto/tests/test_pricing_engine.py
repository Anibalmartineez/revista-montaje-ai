import json
from decimal import Decimal
from pathlib import Path

from sistema_presupuesto.backend.pricing_engine import calculate_pricing
from sistema_presupuesto.backend.production_math import estimate_production
from sistema_presupuesto.backend.serializers import quote_request_from_dict

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def catalog_item(catalog, collection, item_id):
    return next(item for item in catalog[collection] if item["id"] == item_id)


def context_for_fixture(name):
    request = quote_request_from_dict(load_json(f"data/fixtures/{name}.json"))
    materiales = load_json("data/catalogo/materiales_default.json")
    maquinas = load_json("data/catalogo/maquinas_default.json")
    procesos = load_json("data/catalogo/procesos_default.json")
    material = catalog_item(materiales, "materiales", request.costos.material_id)
    machine = catalog_item(maquinas, "maquinas", request.costos.maquina_id)
    process_items = tuple(catalog_item(procesos, "procesos", pid) for pid in request.costos.procesos_ids)
    production = estimate_production(request, machine)
    return request, production, material, machine, process_items


def test_pricing_reconciles_line_items_to_subtotal():
    request, production, material, machine, processes = context_for_fixture("quote_request_tarjeta")

    pricing = calculate_pricing(request, production, material, machine, processes)

    line_total = sum((item.subtotal for item in pricing.items), Decimal("0"))
    assert line_total == pricing.costo_tecnico


def test_markup_and_margin_produce_different_base_prices():
    request, production, material, machine, processes = context_for_fixture("quote_request_volante")
    margin_pricing = calculate_pricing(request, production, material, machine, processes)
    markup_request_payload = load_json("data/fixtures/quote_request_volante.json")
    markup_request_payload["costos"]["margen_pct"] = None
    markup_request_payload["costos"]["markup_pct"] = "30"
    markup_request = quote_request_from_dict(markup_request_payload)

    markup_pricing = calculate_pricing(markup_request, production, material, machine, processes)

    assert margin_pricing.precio_antes_impuestos != markup_pricing.precio_antes_impuestos
    assert margin_pricing.margen_tipo == "margen_sobre_venta"
    assert markup_pricing.margen_tipo == "markup_sobre_costo"


def test_taxes_are_applied_after_base_price():
    request, production, material, machine, processes = context_for_fixture("quote_request_volante")

    pricing = calculate_pricing(request, production, material, machine, processes)

    tax_total = sum((tax.monto for tax in pricing.impuestos if not tax.incluido), Decimal("0"))
    assert pricing.precio_final == pricing.precio_antes_impuestos + tax_total
    assert tax_total > Decimal("0")

