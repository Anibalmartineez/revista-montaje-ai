import io
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

import fitz
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from montaje import montar_pdf
from montaje_offset import montar_pliego_offset, calcular_distribucion


def _crear_pdf_simple(path, paginas):
    c = canvas.Canvas(str(path), pagesize=(100 * mm, 100 * mm))
    for i in range(paginas):
        c.drawString(10, 10, f"p{i}")
        c.showPage()
    c.save()


def test_rotacion_automatica(monkeypatch, tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "salida.pdf"
    _crear_pdf_simple(input_pdf, 4)

    angulos = []
    original_rotate = Image.Image.rotate

    def registrar_rotacion(self, angle, expand=True):
        angulos.append(angle)
        return original_rotate(self, angle, expand=expand)

    monkeypatch.setattr(Image.Image, "rotate", registrar_rotacion)
    montar_pdf(str(input_pdf), str(output_pdf), paginas_por_cara=2)

    assert angulos.count(180) == 2
    assert all(a == 180 for a in angulos)


def test_generacion_multiples_pliegos(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "salida.pdf"
    _crear_pdf_simple(input_pdf, 16)

    montar_pdf(str(input_pdf), str(output_pdf), paginas_por_cara=4)
    doc = fitz.open(str(output_pdf))
    assert len(doc) == 4
    doc.close()


def test_cache_de_imagenes(monkeypatch, tmp_path):
    import montaje_offset

    blanco = Image.new("RGB", (10, 10), "white")
    buffer = io.BytesIO()
    blanco.save(buffer, format="PNG")
    buffer.seek(0)
    reader = ImageReader(buffer)

    llamadas = []

    def falso_pdf_a_imagen(path, sangrado):
        llamadas.append(path)
        return reader

    monkeypatch.setattr(montaje_offset, "_pdf_a_imagen_con_sangrado", falso_pdf_a_imagen)

    montar_pliego_offset(["falso.pdf"], "700x1000", (50, 50), output_dir=str(tmp_path))
    assert len(llamadas) == 1


def test_calculo_correcto_espaciados():
    cols, rows, total = calcular_distribucion(
        100, 100, 30, 30, 10, 10, 10, 10, 5, 5, 0
    )
    assert (cols, rows, total) == (2, 2, 4)
