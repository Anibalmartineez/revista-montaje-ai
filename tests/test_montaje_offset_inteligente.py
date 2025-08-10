import io
import tempfile
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

import os
os.environ.setdefault("OPENAI_API_KEY", "test")

import pytest
from app import app
from montaje_offset_inteligente import (
    obtener_dimensiones_pdf,
    calcular_posiciones,
    montar_pliego_offset_inteligente,
)


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
    posiciones = calcular_posiciones(
        disenos, 300, 200, margen=10, separacion=5, sangrado=0
    )
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


def test_calcular_posiciones_centrado():
    disenos = [
        {"archivo": "a.pdf", "ancho": 100, "alto": 50},
        {"archivo": "b.pdf", "ancho": 80, "alto": 40},
    ]
    posiciones = calcular_posiciones(
        disenos,
        300,
        200,
        margen=10,
        separacion=5,
        sangrado=0,
        centrar=True,
    )
    assert len(posiciones) == 2
    top = max(p["y"] + p["alto"] for p in posiciones)
    bottom = min(p["y"] for p in posiciones)
    assert top - bottom == 50
    assert abs(bottom - (200 - top)) < 1e-6


def test_calcular_posiciones_alinear_filas():
    disenos = [
        {"archivo": "a.pdf", "ancho": 50, "alto": 40},
        {"archivo": "b.pdf", "ancho": 50, "alto": 40},
        {"archivo": "c.pdf", "ancho": 50, "alto": 40},
    ]
    posiciones = calcular_posiciones(
        disenos,
        200,
        200,
        margen=10,
        separacion=4,
        sangrado=0,
        alinear_filas=True,
    )
    assert len(posiciones) == 3
    # Todas las etiquetas deben estar en la misma fila con separación uniforme
    xs = [p["x"] for p in posiciones]
    assert xs[1] - xs[0] == pytest.approx(54)
    assert xs[2] - xs[1] == pytest.approx(54)
    ys = {p["y"] for p in posiciones}
    assert len(ys) == 1


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_montaje_offset_inteligente_con_parametros(client):
    pdf_bytes = io.BytesIO()
    c = canvas.Canvas(pdf_bytes, pagesize=(100 * mm, 100 * mm))
    c.drawString(10, 10, "test")
    c.save()
    pdf_bytes.seek(0)

    data = {
        "pliego": "personalizado",
        "ancho_pliego_custom": "700",
        "alto_pliego_custom": "1000",
        "espaciado_horizontal": "5",
        "espaciado_vertical": "5",
        "margen_izq": "10",
        "margen_der": "10",
        "margen_sup": "10",
        "margen_inf": "10",
        "preferir_horizontal": "on",
        "separacion": "4",
    }
    data["archivos[]"] = (pdf_bytes, "ejemplo.pdf")
    data["repeticiones_0"] = "2"

    response = client.post(
        "/montaje_offset_inteligente",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200


def test_calcular_posiciones_forzar_grilla():
    disenos = (
        [{"archivo": "a.pdf", "ancho": 100, "alto": 50}] * 6
        + [{"archivo": "b.pdf", "ancho": 80, "alto": 60}] * 4
    )
    posiciones = calcular_posiciones(
        disenos,
        500,
        400,
        margen=10,
        separacion=5,
        sangrado=0,
        forzar_grilla=True,
        debug=True,
    )
    assert len(posiciones) == 10

    # Comprobamos que las columnas tienen el mismo ancho y separación
    from collections import defaultdict

    columnas = defaultdict(list)
    for pos in posiciones:
        columnas[round(pos["x"], 5)].append(pos)

    xs = sorted(columnas.keys())
    for i in range(len(xs) - 1):
        ancho_col = columnas[xs[i]][0]["celda_ancho"]
        assert xs[i] + ancho_col + 5 == pytest.approx(xs[i + 1])

    # Todas las filas comparten altura y separación vertical
    filas = defaultdict(list)
    for pos in posiciones:
        # El borde superior de la fila coincide con el borde superior del diseño
        top = pos["y"] + pos["alto"]
        filas[round(top, 5)].append(pos)

    tops = sorted(filas.keys(), reverse=True)
    for i in range(len(tops) - 1):
        alto_f = filas[tops[i]][0]["celda_alto"]
        assert tops[i] - alto_f - 5 == pytest.approx(tops[i + 1])


def _crear_pdf_temporal(ancho_mm: float, alto_mm: float) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    c = canvas.Canvas(tmp.name, pagesize=(ancho_mm * mm, alto_mm * mm))
    c.drawString(10, 10, "test")
    c.save()
    tmp.close()
    return tmp.name


def test_montar_pliego_sin_rotacion_generando_sobrantes(tmp_path):
    pdf = _crear_pdf_temporal(70, 50)
    resumen = tmp_path / "resumen.html"
    montar_pliego_offset_inteligente(
        [(pdf, 2)],
        130,
        90,
        separacion=0,
        sangrado=1,
        margen_izq=10,
        margen_der=10,
        margen_sup=5,
        margen_inf=5,
        resumen_path=str(resumen),
    )
    contenido = resumen.read_text(encoding="utf-8")
    assert "No se pudieron colocar" in contenido


def test_montar_pliego_con_rotacion_coloca_todas(tmp_path):
    pdf = _crear_pdf_temporal(70, 50)
    resumen = tmp_path / "resumen.html"
    montar_pliego_offset_inteligente(
        [(pdf, 2)],
        130,
        90,
        separacion=0,
        sangrado=1,
        margen_izq=10,
        margen_der=10,
        margen_sup=5,
        margen_inf=5,
        permitir_rotacion=True,
        resumen_path=str(resumen),
    )
    contenido = resumen.read_text(encoding="utf-8")
    assert "No se pudieron colocar" not in contenido

def test_montar_pliego_offset_cache(monkeypatch, tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf2 = tmp_path / "b.pdf"

    for pdf in (pdf1, pdf2):
        c = canvas.Canvas(str(pdf), pagesize=(50 * mm, 50 * mm))
        c.drawString(10, 10, "test")
        c.save()

    original = montaje_offset_inteligente._pdf_a_imagen_con_sangrado
    calls = {"count": 0}

    def wrapper(path, sangrado, *args, **kwargs):
        calls["count"] += 1
        return original(path, sangrado, *args, **kwargs)

    monkeypatch.setattr(
        montaje_offset_inteligente, "_pdf_a_imagen_con_sangrado", wrapper
    )

    output = tmp_path / "out.pdf"
    montaje_offset_inteligente.montar_pliego_offset_inteligente(
        [(str(pdf1), 3), (str(pdf2), 2)],
        300,
        300,
        output_path=str(output),
    )
    assert calls["count"] == 2
    assert output.exists()
