import os
import fitz
from typing import List, Dict, Any
from flask import current_app


def generar_preview_diagnostico(pdf_path: str, advertencias: List[Dict[str, Any]] | None, dpi: int = 150) -> tuple[str, str, List[Dict[str, Any]]]:
    """Genera una imagen PNG del PDF para usar como base de superposición.

    Devuelve una tupla con la ruta absoluta del archivo generado, la ruta
    relativa para usar con ``url_for('static', filename=...)`` y la lista de
    advertencias con las coordenadas escaladas al ``dpi`` solicitado.
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    static_dir = getattr(current_app, "static_folder", "static")
    output_folder = os.path.join(static_dir, "previews")
    os.makedirs(output_folder, exist_ok=True)
    imagen_path = os.path.join(output_folder, "preview_diagnostico.png")
    pix.save(imagen_path)
    doc.close()

    scale = dpi / 72.0
    overlay_escalado: List[Dict[str, Any]] = []
    if advertencias:
        for adv in advertencias:
            bbox = adv.get("bbox")
            if bbox and len(bbox) == 4:
                adv_scaled = adv.copy()
                adv_scaled["bbox"] = [coord * scale for coord in bbox]
                overlay_escalado.append(adv_scaled)

    imagen_rel = os.path.join("previews", "preview_diagnostico.png")
    return imagen_path, imagen_rel, overlay_escalado
