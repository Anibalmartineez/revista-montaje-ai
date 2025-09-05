import os
import fitz
from PIL import Image
from simulacion import generar_preview_virtual


def test_generar_preview_virtual_overlay(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    doc.new_page(width=100, height=100)
    doc.save(pdf_path)
    doc.close()

    advertencias = [
        {
            "page": 0,
            "bbox": [10, 10, 60, 60],
            "tipo": "texto_pequeno",
            "label": "Texto <4pt",
        }
    ]

    out_dir = tmp_path / "out"
    paths = generar_preview_virtual(str(pdf_path), advertencias=advertencias, dpi=72, output_dir=str(out_dir))
    assert len(paths) == 1
    assert os.path.exists(paths[0])

    img = Image.open(paths[0])
    # Pixel inside the warning box should not be pure white due to overlay
    pixel = img.getpixel((20, 20))
    assert pixel != (255, 255, 255)
