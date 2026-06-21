import json
from decimal import Decimal
from pathlib import Path

from sistema_presupuesto.backend.serializers import quote_request_from_dict

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_quote_request_serializer_uses_decimal_for_numeric_fields():
    payload = load_json("data/fixtures/quote_request_volante.json")

    model = quote_request_from_dict(payload)

    assert isinstance(model.producto.cantidad, Decimal)
    assert isinstance(model.producto.ancho_mm, Decimal)
    assert isinstance(model.costos.margen_pct, Decimal)
    assert model.costos.markup_pct is None


def test_quote_request_serializer_preserves_catalog_ids():
    payload = load_json("data/fixtures/quote_request_tarjeta.json")

    model = quote_request_from_dict(payload)

    assert model.costos.material_id == "cartulina_300"
    assert model.costos.maquina_id == "offset_4_colores"
    assert model.costos.procesos_ids == ("corte_guillotina", "redondeado_esquinas")
