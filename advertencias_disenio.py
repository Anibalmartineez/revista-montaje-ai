import fitz
from typing import List, Dict, Any

from diagnostico_flexo import filtrar_objetos_sistema, consolidar_advertencias
from utils import convertir_pts_a_mm

PT_PER_MM = 72 / 25.4


def _color_to_cmyk(color: Any) -> str:
    """Convierte un valor de color RGB o entero a una cadena CMYK."""
    try:
        if isinstance(color, int):
            r = (color >> 16) & 255
            g = (color >> 8) & 255
            b = color & 255
        elif isinstance(color, (list, tuple)) and len(color) >= 3:
            r, g, b = [int(c * 255) if isinstance(c, float) and c <= 1 else int(c) for c in color[:3]]
        else:
            r = g = b = 0
        c = 1 - r / 255
        m = 1 - g / 255
        y = 1 - b / 255
        k = min(c, m, y)
        if k < 1:
            c = (c - k) / (1 - k)
            m = (m - k) / (1 - k)
            y = (y - k) / (1 - k)
        else:
            c = m = y = 0
        return f"C{int(c*100)}M{int(m*100)}Y{int(y*100)}K{int(k*100)}"
    except Exception:
        return "C0M0Y0K0"


def verificar_textos_pequenos(contenido: Dict[str, Any]) -> tuple[List[str], List[Dict[str, Any]]]:
    advertencias: List[str] = []
    overlay: List[Dict[str, Any]] = []
    encontrados = False
    for bloque in contenido.get("blocks", []):
        if "lines" in bloque:
            for l in bloque["lines"]:
                for s in l.get("spans", []):
                    size = s.get("size", 0)
                    fuente = s.get("font", "")
                    if size < 4:
                        encontrados = True
                        advertencias.append(
                            f"<span class='icono warn'>⚠️</span> Texto pequeño detectado: '<b>{s.get('text', '')}</b>' ({round(size, 1)}pt, fuente: {fuente}). Riesgo de pérdida en impresión."
                        )
                        bbox = s.get("bbox")
                        if bbox:
                            overlay.append(
                                {
                                    "id": "sistema_texto_pequeno",
                                    "tipo": "texto_pequeno",
                                    "bbox": list(bbox),
                                    "etiqueta": f"{round(size, 1)} pt",
                                    "tamano": round(size, 1),
                                    "color": _color_to_cmyk(s.get("color", 0)),
                                }
                            )
    if not encontrados:
        advertencias.append("<span class='icono ok'>✔️</span> No se encontraron textos menores a 4 pt.")
    return advertencias, overlay


def verificar_lineas_finas_v2(page: fitz.Page, material: str) -> tuple[List[str], List[Dict[str, Any]]]:
    mins = {"film": 0.12, "papel": 0.20, "etiqueta adhesiva": 0.18}
    thr = mins.get((material or "").strip().lower(), 0.20)
    min_detectada = None
    n_riesgo = 0
    overlay: List[Dict[str, Any]] = []
    dibujos = filtrar_objetos_sistema(page.get_drawings(), None)
    for d in dibujos:
        w_pt = (d.get("width", 0) or 0)
        if w_pt <= 0:
            continue
        w_mm = w_pt / PT_PER_MM
        min_detectada = w_mm if min_detectada is None else min(min_detectada, w_mm)
        if w_mm < thr:
            n_riesgo += 1
            bbox = d.get("bbox") or d.get("rect")
            if bbox:
                overlay.append(
                    {
                        "id": "sistema_trazo_fino",
                        "tipo": "trazo_fino",
                        "bbox": list(bbox),
                        "etiqueta": f"{w_mm:.2f} mm",
                    }
                )
    if n_riesgo:
        advertencias = [
            f"<li><span class='icono warn'>⚠️</span> {n_riesgo} trazos por debajo de <b>{thr:.2f} mm</b>. Mínimo detectado: <b>{min_detectada:.2f} mm</b>.</li>"
        ]
    else:
        advertencias = [
            f"<li><span class='icono ok'>✔️</span> Trazos ≥ <b>{thr:.2f} mm</b>. Mínimo detectado: <b>{(min_detectada or thr):.2f} mm</b>.</li>"
        ]
    return advertencias, overlay


def verificar_modo_color(path_pdf: str) -> tuple[List[str], List[Dict[str, Any]]]:
    advertencias: List[str] = []
    overlay: List[Dict[str, Any]] = []
    try:
        doc = fitz.open(path_pdf)
        for page_num, page in enumerate(doc, start=1):
            for xref, *_ in page.get_images(full=True):
                cs = ""
                try:
                    info = doc.extract_image(xref)
                    cs = (info.get("colorspace") or "").upper()
                except Exception:
                    cs = ""
                for rect in page.get_image_rects(xref):
                    bbox = [rect.x0, rect.y0, rect.x1, rect.y1]
                    if cs == "RGB":
                        advertencias.append(
                            f"<span class='icono error'>❌</span> Imagen en RGB detectada en la página {page_num}. Convertir a CMYK."
                        )
                        overlay.append(
                            {
                                "id": "sistema_imagen_fuera_cmyk",
                                "tipo": "imagen_fuera_cmyk",
                                "bbox": bbox,
                                "etiqueta": "RGB",
                            }
                        )
                    elif cs and cs not in {"CMYK", "DEVICECMYK", "GRAY", "DEVICEGRAY"}:
                        advertencias.append(
                            f"<span class='icono warn'>⚠️</span> Imagen en {cs} detectada en la página {page_num}. Verificar modo de color."
                        )
                        overlay.append(
                            {
                                "id": "sistema_imagen_fuera_cmyk",
                                "tipo": "imagen_fuera_cmyk",
                                "bbox": bbox,
                                "etiqueta": cs,
                            }
                        )
                    elif cs in {"GRAY", "DEVICEGRAY"}:
                        advertencias.append(
                            f"<span class='icono warn'>⚠️</span> Imagen en escala de grises detectada en la página {page_num}. Verificar si es intencional."
                        )
                        overlay.append(
                            {
                                "id": "sistema_imagen_fuera_cmyk",
                                "tipo": "imagen_fuera_cmyk",
                                "bbox": bbox,
                                "etiqueta": "Gray",
                            }
                        )
        if not advertencias:
            advertencias.append("<span class='icono ok'>✔️</span> Todas las imágenes están en modo CMYK o escala de grises.")
        doc.close()
    except Exception as e:
        advertencias.append(f"<span class='icono warn'>⚠️</span> No se pudo verificar el modo de color: {str(e)}")
    return advertencias, overlay


def revisar_sangrado(pagina: fitz.Page, sangrado_esperado: float = 3) -> tuple[List[str], List[Dict[str, Any]]]:
    advertencias: List[str] = []
    overlay: List[Dict[str, Any]] = []
    media = pagina.rect
    contenido = pagina.get_text("dict")
    for bloque in contenido.get("blocks", []):
        bbox = bloque.get("bbox")
        if bbox:
            x0, y0, x1, y1 = bbox
            margen_izq = convertir_pts_a_mm(x0)
            margen_der = convertir_pts_a_mm(media.width - x1)
            margen_sup = convertir_pts_a_mm(y0)
            margen_inf = convertir_pts_a_mm(media.height - y1)
            if min(margen_izq, margen_der, margen_sup, margen_inf) < sangrado_esperado:
                overlay.append(
                    {
                        "id": "sistema_cerca_borde",
                        "tipo": "cerca_borde",
                        "bbox": list(bbox),
                    }
                )
    if overlay:
        advertencias.append(
            "<span class='icono warn'>⚠️</span> Elementos del diseño muy cercanos al borde. Verificar sangrado mínimo de 3 mm."
        )
    else:
        advertencias.append(
            "<span class='icono ok'>✔️</span> Margen de seguridad adecuado respecto al sangrado."
        )
    return advertencias, overlay


def analizar_advertencias_disenio(
    path_pdf: str,
    material: str = "",
    pagina: fitz.Page | None = None,
    contenido: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    doc = None
    if pagina is None or contenido is None:
        doc = fitz.open(path_pdf)
        pagina = doc[0]
        contenido = pagina.get_text("dict")
    textos_adv, overlay_textos = verificar_textos_pequenos(contenido)
    lineas_adv, overlay_lineas = verificar_lineas_finas_v2(pagina, material)
    modo_color_adv, overlay_color = verificar_modo_color(path_pdf)
    sangrado_adv, overlay_sangrado = revisar_sangrado(pagina)
    overlay = consolidar_advertencias(overlay_textos, overlay_lineas, overlay_color, overlay_sangrado)
    if doc:
        doc.close()
    return {
        "textos": textos_adv,
        "lineas": lineas_adv,
        "modo_color": modo_color_adv,
        "sangrado": sangrado_adv,
        "overlay": overlay,
    }
