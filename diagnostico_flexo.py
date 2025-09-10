import os
import fitz
import numpy as np
from typing import List, Dict, Any
from flask import current_app
from PIL import Image, ImageDraw


def generar_preview_diagnostico(
    pdf_path: str, advertencias: List[Dict[str, Any]] | None, dpi: int = 150
) -> tuple[str, str, str, List[Dict[str, Any]]]:
    """Genera imágenes PNG del PDF y una versión con bloques de color.

    Devuelve una tupla con la ruta absoluta de la imagen base, la ruta relativa
    de la imagen base, la ruta relativa de la imagen anotada y la lista de
    advertencias con las coordenadas escaladas al ``dpi`` solicitado para su
    uso interactivo en HTML.
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    static_dir = getattr(current_app, "static_folder", "static")
    output_folder = os.path.join(static_dir, "previews")
    os.makedirs(output_folder, exist_ok=True)

    base_path = os.path.join(output_folder, "preview_diagnostico.png")
    pix.save(base_path)
    doc.close()

    # Imagen con bloques coloreados para descarga
    anotada_path = os.path.join(output_folder, "preview_diagnostico_iconos.png")
    base_img = Image.open(base_path).convert("RGBA")
    draw = ImageDraw.Draw(base_img)

    scale = dpi / 72.0
    size = 16
    colores = {
        "texto_pequeno": "red",
        "trama_debil": "purple",
        "imagen_baja": "orange",
        "overprint": "blue",
        "sin_sangrado": "darkgreen",
    }

    advertencias_iconos: List[Dict[str, Any]] = []
    for adv in consolidar_advertencias(advertencias):
        bbox = adv.get("bbox")
        if not bbox or len(bbox) != 4:
            continue

        x0 = int(bbox[0] * scale)
        y0 = int(bbox[1] * scale)
        x1 = int(bbox[2] * scale)
        y1 = int(bbox[3] * scale)
        tipo = adv.get("tipo", "")
        color = colores.get(tipo, "red")
        # Rectángulo pequeño en la imagen descargable
        draw.rectangle([x0, y0, x0 + size, y0 + size], fill=color)

        advertencias_iconos.append(
            {
                "tipo": tipo,
                "pos": [x0, y0],  # compatibilidad con versiones previas
                "bbox": [x0, y0, x1, y1],
                "mensaje": adv.get("mensaje", ""),
                "pagina": adv.get("pagina", 1),
                "nivel": adv.get("nivel", "leve"),
            }
        )

    base_img.save(anotada_path)

    imagen_rel = os.path.join("previews", "preview_diagnostico.png")
    anotada_rel = os.path.join("previews", "preview_diagnostico_iconos.png")
    return base_path, imagen_rel, anotada_rel, advertencias_iconos


# ---------------------------------------------------------------------------
# Utilidades de diagnóstico flexográfico
# ---------------------------------------------------------------------------
def detectar_trama_debil_negro(
    img: np.ndarray, umbral: float = 5.0
) -> List[Dict[str, Any]]:
    """Evalúa trama débil en el canal negro.

    Si la cobertura del canal K es 0%, la evaluación se omite.
    Devuelve una lista con advertencias encontradas, vacía si no hay riesgo.
    """

    resultados: List[Dict[str, Any]] = []
    if img.shape[2] < 4:
        return resultados

    canal_k = img[:, :, 3]
    if not np.any(canal_k):
        return resultados

    limite = umbral / 100.0 * 255.0
    mask = (canal_k > 0) & (canal_k < limite)
    if np.any(mask):
        resultados.append(
            {"mensaje": "Trama débil detectada en canal negro", "nivel": "medio"}
        )

    return resultados


def filtrar_objetos_sistema(
    objetos: List[Dict[str, Any]], advertencias: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Excluye del análisis los trazos generados por el sistema (overlays)."""

    advertencias_bboxes = {
        tuple(adv.get("bbox")) for adv in advertencias or [] if adv.get("bbox")
    }
    filtrados: List[Dict[str, Any]] = []
    for obj in objetos:
        bbox = tuple(obj.get("bbox")) if obj.get("bbox") else None
        if obj.get("id", "").startswith("sistema"):
            continue
        if bbox and bbox in advertencias_bboxes:
            continue
        filtrados.append(obj)
    return filtrados


def consolidar_advertencias(*listas: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    """Combina múltiples listas de advertencias evitando duplicados.

    Una advertencia se considera duplicada cuando coinciden su tipo o mensaje y
    su "bbox"."""

    combinadas: List[Dict[str, Any]] = []
    vistos = set()
    for lista in listas:
        for adv in lista or []:
            tipo = adv.get("tipo")
            mensaje = adv.get("mensaje")
            if not tipo and not mensaje:
                combinadas.append(adv)
                continue
            clave = (
                tipo or mensaje,
                tuple(adv.get("bbox")) if adv.get("bbox") else None,
            )
            if clave in vistos:
                continue
            vistos.add(clave)
            combinadas.append(adv)
    return combinadas


def resumen_advertencias(advertencias: List[Dict[str, Any]]) -> str:
    """Genera un resumen global de advertencias clasificado por nivel."""

    advertencias = consolidar_advertencias(advertencias)
    if not advertencias:
        return "✅ Archivo sin riesgos detectados. Listo para enviar a clichés."

    niveles = {"critico": 0, "medio": 0, "leve": 0}
    for adv in advertencias:
        nivel = adv.get("nivel", "leve")
        if nivel not in niveles:
            nivel = "leve"
        niveles[nivel] += 1

    total = sum(niveles.values())
    return (
        f"Este archivo presenta {total} advertencias: "
        f"{niveles['critico']} críticas (🔴), "
        f"{niveles['medio']} medias (🟡) y "
        f"{niveles['leve']} leves (🟢)."
    )


def nivel_riesgo_global(advertencias: List[Dict[str, Any]]) -> str:
    """Calcula el nivel global de riesgo basado en las advertencias."""

    advertencias = consolidar_advertencias(advertencias)
    if any(adv.get("nivel") == "critico" for adv in advertencias):
        return "alto"
    if any(adv.get("nivel") == "medio" for adv in advertencias):
        return "medio"
    return "bajo"


def semaforo_riesgo(advertencias: List[Dict[str, Any]]) -> str:
    """Representación con emoji del nivel de riesgo."""

    nivel = nivel_riesgo_global(advertencias)
    return {"alto": "🔴", "medio": "🟡", "bajo": "🟢"}[nivel]
