import os
import fitz
import numpy as np
from typing import List, Dict, Any, Tuple
from flask import current_app


def generar_preview_diagnostico(
    pdf_path: str, advertencias: List[Dict[str, Any]] | None, dpi: int = 150
) -> tuple[str, str, List[Dict[str, Any]]]:
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


# ---------------------------------------------------------------------------
# Utilidades de diagnóstico flexográfico
# ---------------------------------------------------------------------------


def calcular_cobertura_y_tac(
    pdf_path: str, dpi: int = 72
) -> Tuple[Dict[str, float], float]:
    """Calcula cobertura por canal CMYK y el TAC p95 real del diseño.

    ``cobertura`` representa el porcentaje promedio de tinta en cada canal y
    ``tac_p95`` el percentil 95 del Total Area Coverage.
    """

    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    # Obtiene la imagen en CMYK y en RGB para filtrar los píxeles casi blancos
    pix_cmyk = page.get_pixmap(matrix=mat, colorspace=fitz.csCMYK, alpha=False)
    pix_rgb = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
    img_cmyk = np.frombuffer(pix_cmyk.samples, dtype=np.uint8).reshape(
        pix_cmyk.height, pix_cmyk.width, pix_cmyk.n
    )
    img_rgb = np.frombuffer(pix_rgb.samples, dtype=np.uint8).reshape(
        pix_rgb.height, pix_rgb.width, pix_rgb.n
    )
    doc.close()

    # Máscara para identificar píxeles casi blancos (RGB > 245)
    mask_white = (
        (img_rgb[..., 0] > 245)
        & (img_rgb[..., 1] > 245)
        & (img_rgb[..., 2] > 245)
    )
    # Se ignoran asignándoles 0 en los canales CMYK
    img_cmyk = img_cmyk.astype(np.float32)
    img_cmyk[mask_white] = 0

    canales = ["Cyan", "Magenta", "Amarillo", "Negro"]
    coberturas = {
        canal: float(img_cmyk[:, :, i].mean() / 255.0 * 100.0)
        for i, canal in enumerate(canales)
    }

    coberturas_cmyk_sumadas = img_cmyk.sum(axis=2) / 255.0 * 100.0
    tac_p95 = float(np.percentile(coberturas_cmyk_sumadas, 95))

    return coberturas, tac_p95


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


def resumen_advertencias(advertencias: List[Dict[str, Any]]) -> str:
    """Genera un resumen global de advertencias clasificado por nivel."""

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

    if any(adv.get("nivel") == "critico" for adv in advertencias):
        return "alto"
    if any(adv.get("nivel") == "medio" for adv in advertencias):
        return "medio"
    return "bajo"


def semaforo_riesgo(advertencias: List[Dict[str, Any]]) -> str:
    """Representación con emoji del nivel de riesgo."""

    nivel = nivel_riesgo_global(advertencias)
    return {"alto": "🔴", "medio": "🟡", "bajo": "🟢"}[nivel]
