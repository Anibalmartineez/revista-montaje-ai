import tempfile
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from montaje_offset_inteligente import obtener_dimensiones_pdf, calcular_posiciones


def test_obtener_dimensiones_pdf():
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        c = canvas.Canvas(tmp.name, pagesize=(100 * mm, 50 * mm))
        c.drawString(10, 10, "test")
        c.save()
        ancho, alto = obtener_dimensiones_pdf(tmp.name)
        assert round(ancho) == 100
        assert round(alto) == 50


def test_calcular_posiciones_no_overlap():
    disenos = [
        {"archivo": "a.pdf", "ancho": 100, "alto": 50},
        {"archivo": "b.pdf", "ancho": 80, "alto": 40},
    ]
    posiciones = calcular_posiciones(disenos, 300, 200, margen=10, espacio=5, sangrado=0)
    assert len(posiciones) == 2
    a, b = posiciones
    overlap = not (
        a["x"] + a["ancho"] <= b["x"]
        or b["x"] + b["ancho"] <= a["x"]
        or a["y"] + a["alto"] <= b["y"]
        or b["y"] + b["alto"] <= a["y"]
    )
    assert not overlap
    for pos in posiciones:
        assert pos["x"] >= 10 and pos["y"] >= 10
        assert pos["x"] + pos["ancho"] <= 300 - 10
        assert pos["y"] + pos["alto"] <= 200 - 10


def test_calcular_posiciones_centrado_vertical():
    disenos = [
        {"archivo": "a.pdf", "ancho": 100, "alto": 50},
        {"archivo": "b.pdf", "ancho": 80, "alto": 40},
    ]
    posiciones = calcular_posiciones(
        disenos,
        300,
        200,
        margen=10,
        espacio=5,
        sangrado=0,
        centrar_vertical=True,
    )
    assert len(posiciones) == 2
    top = max(p["y"] + p["alto"] for p in posiciones)
    bottom = min(p["y"] for p in posiciones)
    # Con centrado vertical los márgenes superior e inferior deben ser iguales
    assert top - bottom == 50  # altura utilizada
    assert abs(bottom - (200 - top)) < 1e-6
