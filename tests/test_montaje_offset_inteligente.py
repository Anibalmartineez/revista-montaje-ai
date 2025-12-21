import io
import json
import shutil
import tempfile
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

import os
import uuid
os.environ.setdefault("OPENAI_API_KEY", "test")

import pytest
import montaje_offset_inteligente
from app import app
from routes import POST_EDITOR_DIR, LAYOUT_FILENAME
from montaje_offset_inteligente import (
    obtener_dimensiones_pdf,
    calcular_posiciones,
    montar_pliego_offset_inteligente,
)
from pdf_compat import to_adobe_compatible, to_pdfx1a


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


def test_modo_ia_generates_layout_json(client, monkeypatch):
    job_token = "testjob123456"

    class _FakeUUID:
        def __init__(self, value):
            self.hex = value

    monkeypatch.setattr(uuid, "uuid4", lambda: _FakeUUID(job_token))

    job_dir = Path(app.static_folder) / POST_EDITOR_DIR / job_token[:12]
    if job_dir.exists():
        shutil.rmtree(job_dir)

    pdf_bytes = io.BytesIO()
    c = canvas.Canvas(pdf_bytes, pagesize=(80 * mm, 50 * mm))
    c.drawString(5, 5, "pieza")
    c.save()
    pdf_bytes.seek(0)

    data = {
        "pliego": "personalizado",
        "ancho_pliego_custom": "500",
        "alto_pliego_custom": "700",
        "espaciado_horizontal": "0",
        "espaciado_vertical": "0",
        "margen_izq": "10",
        "margen_der": "10",
        "margen_sup": "10",
        "margen_inf": "10",
        "separacion": "4",
        "modo_ia": "1",
    }
    data["archivos[]"] = (pdf_bytes, "pieza.pdf")
    data["repeticiones_0"] = "1"

    resp = client.post(
        "/montaje_offset_inteligente",
        data=data,
        content_type="multipart/form-data",
    )

    assert resp.status_code == 200

    layout_path = (
        Path(app.static_folder)
        / POST_EDITOR_DIR
        / job_token[:12]
        / LAYOUT_FILENAME
    )
    assert layout_path.exists(), "El layout JSON no se generó en modo IA"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    assert layout.get("items"), "El layout debe incluir piezas montadas"
    assert layout.get("sheet", {}).get("w_mm")


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


def test_manual_positions_preview_and_pdf(tmp_path):
    pdf = _crear_pdf_temporal(20, 10)
    posiciones = [
        {"file_idx": 0, "x_mm": 10, "y_mm": 20, "w_mm": 20, "h_mm": 10, "rot": False}
    ]
    prev = tmp_path / "prev.png"
    res = montaje_offset_inteligente.montar_pliego_offset_inteligente(
        [(pdf, 1)],
        100,
        100,
        sangrado=0,
        estrategia="manual",
        posiciones_manual=posiciones,
        preview_path=str(prev),
        devolver_posiciones=True,
        centrar=False,
    )
    assert prev.exists()
    assert res["positions"][0]["x_mm"] == pytest.approx(10.0)
    out = tmp_path / "out.pdf"
    montaje_offset_inteligente.montar_pliego_offset_inteligente(
        [(pdf, 1)],
        100,
        100,
        sangrado=0,
        estrategia="manual",
        posiciones_manual=posiciones,
        output_path=str(out),
        centrar=False,
    )
    assert out.exists()


def _crear_pdf_simple(tmp_path: Path, nombre: str = "simple.pdf") -> str:
    pdf_path = tmp_path / nombre
    c = canvas.Canvas(str(pdf_path), pagesize=(50 * mm, 50 * mm))
    c.rect(5 * mm, 5 * mm, 40 * mm, 40 * mm)
    c.setFillColorRGB(1, 0, 0)
    c.drawString(10, 10, "vector")
    c.save()
    return str(pdf_path)


def test_vector_hybrid_con_sangrado(tmp_path):
    pdf_path = _crear_pdf_simple(tmp_path)
    out_path = tmp_path / "salida_vector_hybrid_bleed.pdf"

    output = montaje_offset_inteligente.montar_pliego_offset_inteligente(
        diseños=[(pdf_path, 1)],
        ancho_pliego=200,
        alto_pliego=200,
        separacion=0,
        sangrado=2,
        espaciado_horizontal=0,
        espaciado_vertical=0,
        output_path=str(out_path),
        output_mode="vector_hybrid",
    )

    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 0
    assert output == str(out_path)


def test_vector_hybrid_sin_sangrado(tmp_path):
    pdf_path = _crear_pdf_simple(tmp_path, "simple_sin_bleed.pdf")
    out_path = tmp_path / "salida_vector_hybrid_sin_bleed.pdf"

    output = montaje_offset_inteligente.montar_pliego_offset_inteligente(
        diseños=[(pdf_path, 1)],
        ancho_pliego=200,
        alto_pliego=200,
        separacion=0,
        sangrado=0,
        espaciado_horizontal=0,
        espaciado_vertical=0,
        output_path=str(out_path),
        output_mode="vector_hybrid",
    )

    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 0
    assert output == str(out_path)


def _crear_pdf_en(tmp_path, nombre: str = "base.pdf") -> str:
    ruta = tmp_path / nombre
    c = canvas.Canvas(str(ruta), pagesize=(100 * mm, 100 * mm))
    c.drawString(20, 20, "compat test")
    c.save()
    return str(ruta)


def test_export_adobe_compatible(tmp_path):
    base_pdf = _crear_pdf_en(tmp_path, "compat_base.pdf")
    out_path = to_adobe_compatible(base_pdf)
    assert out_path is not None
    assert out_path.endswith("_ADOBE.pdf")
    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 0


def test_export_pdfx1a(tmp_path):
    base_pdf = _crear_pdf_en(tmp_path, "compat_base2.pdf")
    out_path = to_pdfx1a(base_pdf)
    assert out_path is not None
    assert out_path.endswith("_PDFX1a.pdf")
    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 0
