import fitz  # PyMuPDF
from PIL import Image
import numpy as np
from io import BytesIO


def corregir_sangrado(input_path, output_path):
    """Replica los bordes de cada página para añadir un sangrado de 3 mm."""
    margen_mm = 3
    dpi = 150
    margen_px = int((margen_mm / 25.4) * dpi)

    def replicar_bordes(img, margen_px):
        arr = np.array(img)
        top = np.tile(arr[0:1, :, :], (margen_px, 1, 1))
        bottom = np.tile(arr[-1:, :, :], (margen_px, 1, 1))
        extended_vertical = np.vstack([top, arr, bottom])
        left = np.tile(extended_vertical[:, 0:1, :], (1, margen_px, 1))
        right = np.tile(extended_vertical[:, -1:, :], (1, margen_px, 1))
        extended_full = np.hstack([left, extended_vertical, right])
        return Image.fromarray(extended_full)

    doc = fitz.open(input_path)
    nuevo_doc = fitz.open()

    for pagina in doc:
        pix = pagina.get_pixmap(dpi=dpi, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_con_sangrado = replicar_bordes(img, margen_px)

        buffer = BytesIO()
        img_con_sangrado.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)

        ancho_pts = img_con_sangrado.width * 72 / dpi
        alto_pts = img_con_sangrado.height * 72 / dpi
        nueva_pagina = nuevo_doc.new_page(width=ancho_pts, height=alto_pts)
        rect = fitz.Rect(0, 0, ancho_pts, alto_pts)
        nueva_pagina.insert_image(rect, stream=buffer)
        buffer.close()

    nuevo_doc.save(output_path)


def redimensionar_pdf(input_path, output_path, nuevo_ancho_mm, nuevo_alto_mm=None):
    """Redimensiona un PDF a un nuevo ancho/alto manteniendo proporciones."""
    doc = fitz.open(input_path)
    nuevo_doc = fitz.open()

    ancho_pts = nuevo_ancho_mm * 72 / 25.4
    if nuevo_alto_mm:
        alto_pts = nuevo_alto_mm * 72 / 25.4
    else:
        pagina = doc[0]
        proporcion = pagina.rect.height / pagina.rect.width
        alto_pts = ancho_pts * proporcion

    for pagina in doc:
        pix = pagina.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        ancho_original = pagina.rect.width
        alto_original = pagina.rect.height
        escala_x = ancho_pts / ancho_original
        escala_y = alto_pts / alto_original
        escala = min(escala_x, escala_y)

        nueva_pagina = nuevo_doc.new_page(width=ancho_pts, height=alto_pts)
        nueva_pagina.show_pdf_page(
            fitz.Rect(0, 0, ancho_pts, alto_pts),
            doc,
            pagina.number,
            rotate=0,
            clip=None,
            oc=0,
            overlay=False,
            keep_proportion=True,
            scale=escala
        )

    nuevo_doc.save(output_path)
