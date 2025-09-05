import os
import sys
import pathlib
import fitz
from PIL import Image
from flask import Flask

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from preview_tecnico import analizar_riesgos_pdf, generar_preview_tecnico

def test_generar_preview_tecnico_overlay(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    # Texto pequeño cerca del borde para disparar sangrado insuficiente
    page.insert_text((2, 2), "Hi", fontsize=3)
    doc.save(pdf_path)
    doc.close()

    overlay_info = analizar_riesgos_pdf(str(pdf_path), dpi=72)
    assert os.path.exists(overlay_info["overlay_path"])
    overlay_img = Image.open(overlay_info["overlay_path"])
    assert overlay_img.getbbox() is not None

    app = Flask(__name__)
    app.static_folder = str(tmp_path)
    with app.app_context():
        rel = generar_preview_tecnico(
            str(pdf_path), None, overlay_path=overlay_info["overlay_path"], dpi=overlay_info["dpi"]
        )
    out_path = tmp_path / rel
    assert out_path.exists()
    img = Image.open(out_path)
    sangrado_pts = 3 * 72 / 25.4
    x = int(sangrado_pts * (overlay_info["dpi"] / 72.0))
    pixel = img.getpixel((x, x))
    assert pixel != (255, 255, 255, 255)
