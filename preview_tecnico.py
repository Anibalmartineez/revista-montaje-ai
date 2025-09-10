import os
import uuid
import fitz
import tempfile
from typing import Any, List, Dict
from PIL import Image, ImageDraw
from flask import current_app
from advertencias_disenio import analizar_advertencias_disenio


def analizar_riesgos_pdf(
    pdf_path: str,
    dpi: int = 200,
    advertencias: List[Dict[str, Any]] | None = None,
    material: str = "",
) -> dict:
    """Genera una superposición de advertencias para un PDF."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    size = (pix.width, pix.height)

    if advertencias is None:
        adv_res = analizar_advertencias_disenio(pdf_path, material)
        advertencias = adv_res["overlay"]

    overlay_img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_img, "RGBA")

    sangrado_mm = 3
    sangrado_pts = sangrado_mm * 72 / 25.4
    contenido_cerca_borde = any(adv.get("tipo") == "cerca_borde" for adv in advertencias)

    def dashed_rectangle(draw_obj, box, color, width: int = 2, dash: int = 5):
        x0, y0, x1, y1 = box
        x = x0
        while x < x1:
            draw_obj.line([(x, y0), (min(x + dash, x1), y0)], fill=color, width=width)
            draw_obj.line([(x, y1), (min(x + dash, x1), y1)], fill=color, width=width)
            x += dash * 2
        y = y0
        while y < y1:
            draw_obj.line([(x0, y), (x0, min(y + dash, y1))], fill=color, width=width)
            draw_obj.line([(x1, y), (x1, min(y + dash, y1))], fill=color, width=width)
            y += dash * 2

    for adv in advertencias:
        bbox = adv.get("bbox") or adv.get("box")
        if not bbox or len(bbox) != 4:
            continue
        x0, y0, x1, y1 = [coord * zoom for coord in bbox]
        tipo = (adv.get("tipo") or adv.get("type") or "").lower()
        if tipo == "texto_pequeno":
            draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0, 255), width=2)
            etiqueta = adv.get("etiqueta") or "<4 pt"
            draw.text((x0 + 2, y0 + 2), etiqueta, fill=(255, 0, 0, 255))
        elif tipo in {"trazo_fino", "stroke_fino"}:
            draw.rectangle([x0, y0, x1, y1], outline=(255, 165, 0, 255), width=2)
            etiqueta = adv.get("etiqueta")
            if etiqueta:
                draw.text((x0 + 2, y0 + 2), etiqueta, fill=(255, 165, 0, 255))
        elif tipo == "imagen_fuera_cmyk":
            draw.rectangle([x0, y0, x1, y1], outline=(128, 0, 128, 255), width=2)
            etiqueta = adv.get("etiqueta")
            if etiqueta:
                draw.text((x0 + 2, y0 + 2), etiqueta, fill=(128, 0, 128, 255))
        elif tipo == "cerca_borde":
            dashed_rectangle(draw, [x0, y0, x1, y1], (255, 165, 0, 255), width=2)

    rect_segura = [
        sangrado_pts * zoom,
        sangrado_pts * zoom,
        (page.rect.width - sangrado_pts) * zoom,
        (page.rect.height - sangrado_pts) * zoom,
    ]
    color_sangrado = (255, 0, 0, 255) if contenido_cerca_borde else (0, 0, 255, 255)
    draw.rectangle(rect_segura, outline=color_sangrado, width=3)

    doc.close()
    tmp_dir = tempfile.gettempdir()
    filename = f"preview_tecnico_overlay_{uuid.uuid4().hex}.png"
    tmp_path = os.path.join(tmp_dir, filename)
    overlay_img.save(tmp_path)
    return {"overlay_path": tmp_path, "dpi": dpi, "advertencias": advertencias}


def generar_preview_tecnico(
    pdf_path: str,
    datos_formulario: dict | None,
    overlay_path: str | None = None,
    dpi: int = 200,
) -> str:
    """Genera una vista previa técnica reutilizando los datos de diagnóstico.

    Si ``overlay_path`` está definido, se utiliza la superposición previamente
    calculada; de lo contrario, se genera una imagen vacía (sin advertencias).
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    base = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")

    if overlay_path and os.path.exists(overlay_path):
        overlay_img = Image.open(overlay_path).convert("RGBA")
    else:
        overlay_img = Image.new("RGBA", base.size, (0, 0, 0, 0))

    advertencias: list[Any] = []
    if datos_formulario:
        if isinstance(datos_formulario, list):
            advertencias = datos_formulario
        elif isinstance(datos_formulario, dict):
            adv = datos_formulario.get("advertencias") or datos_formulario.get("warnings")
            if isinstance(adv, dict):
                tmp: list[Any] = []
                for k, v in adv.items():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                item.setdefault("tipo", k)
                                tmp.append(item)
                advertencias = tmp
            elif adv:
                advertencias = adv  # assume list

    print("📌 Advertencias recibidas:", advertencias)

    def dashed_rectangle(draw, box, color, width: int = 2, dash: int = 5):
        x0, y0, x1, y1 = box
        # Horizontal lines
        x = x0
        while x < x1:
            draw.line([(x, y0), (min(x + dash, x1), y0)], fill=color, width=width)
            draw.line([(x, y1), (min(x + dash, x1), y1)], fill=color, width=width)
            x += dash * 2
        y = y0
        while y < y1:
            draw.line([(x0, y), (x0, min(y + dash, y1))], fill=color, width=width)
            draw.line([(x1, y), (x1, min(y + dash, y1))], fill=color, width=width)
            y += dash * 2

    draw = ImageDraw.Draw(overlay_img, "RGBA")
    color_trama = {
        "c": (0, 255, 255, 100),
        "m": (255, 0, 255, 100),
        "y": (255, 255, 0, 100),
        "k": (0, 0, 0, 100),
    }

    if advertencias:
        for adv in advertencias:
            bbox = adv.get("bbox") or adv.get("box")
            if not bbox or len(bbox) != 4:
                continue
            x0, y0, x1, y1 = [coord * zoom for coord in bbox]
            tipo = (adv.get("tipo") or adv.get("type") or "").lower()
            if tipo.startswith("trama_debil"):
                canal = tipo.split("_")[-1][:1]
                color = color_trama.get(canal, (255, 255, 0, 100))
                draw.rectangle([x0, y0, x1, y1], fill=color)
            elif tipo == "texto_pequeno":
                draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0, 255), width=2)
                draw.text((x0 + 2, y0 + 2), "< 4 pt", fill=(255, 0, 0, 255))
            elif tipo in {"trazo_fino", "stroke_fino"}:
                draw.rectangle([x0, y0, x1, y1], outline=(255, 165, 0, 255), width=2)
            elif tipo in {"imagen_fuera_cmyk", "fuera_cmyk", "color_rgb", "rgb"}:
                draw.rectangle([x0, y0, x1, y1], outline=(128, 0, 128, 255), width=2)
                draw.text((x0 + 2, y0 + 2), "RGB", fill=(128, 0, 128, 255))
            elif tipo in {"cerca_borde", "sin_sangrado", "fuera_margen", "fuera_area"}:
                dashed_rectangle(draw, [x0, y0, x1, y1], (255, 165, 0, 255), width=2)
            label = adv.get("label") or adv.get("texto")
            if label:
                draw.text((x0 + 2, y0 + 2), label, fill=(0, 0, 0, 255))
    else:
        # Marca de validación cuando no hay advertencias
        draw.text((10, 10), "✔", fill=(0, 128, 0, 255))

    composed = Image.alpha_composite(base, overlay_img)
    doc.close()

    static_dir = getattr(current_app, "static_folder", "static")
    previews_dir = os.path.join(static_dir, "previews")
    os.makedirs(previews_dir, exist_ok=True)
    # Guardar con nombre único para evitar caché en el navegador
    filename = f"preview_diagnostico_flexo_{uuid.uuid4().hex}.png"
    output_abs = os.path.join(previews_dir, filename)
    composed.save(output_abs)
    # Informar en consola la ruta absoluta de salida
    print("✅ Imagen compuesta guardada en:", output_abs)

    return os.path.join("previews", filename)
