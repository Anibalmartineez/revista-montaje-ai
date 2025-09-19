import math
import os
from collections import Counter

import fitz
import numpy as np
from typing import List, Dict, Any
from flask import current_app
from PIL import Image, ImageDraw


# Descripciones genéricas para cada tipo de advertencia admitido.  Se
# utilizan cuando la advertencia original no provee un texto
# explicativo.  Esto evita mostrar "sin descripción" en la interfaz y
# garantiza que siempre exista un mensaje claro para el usuario.
DESCRIPCIONES_POR_TIPO = {
    "texto_pequeno": "Texto menor a 4pt. Puede no imprimirse correctamente.",
    "trazo_fino": "Línea muy delgada. Riesgo de pérdida en impresión.",
    "cerca_borde": "Elemento fuera del margen de seguridad.",
    "imagen_fuera_cmyk": "Imagen en RGB. Convertir a modo CMYK.",
    "overprint": "Sobreimpresión detectada. Verificar configuración.",
}


def inyectar_parametros_simulacion(
    diagnostico_json: Dict[str, Any] | None, parametros: Dict[str, Any] | None
) -> Dict[str, Any]:
    """Incorpora en ``diagnostico_json`` los parámetros reales de máquina.

    Los sliders de la simulación avanzada y los resúmenes técnicos esperan
    encontrar las claves heredadas (``lpi``, ``bcm``, ``paso``) además de las
    nuevas que vienen del formulario.  Este helper sincroniza ambas fuentes
    reutilizando los valores cargados por el usuario.
    """

    if diagnostico_json is None:
        diagnostico_json = {}
    else:
        diagnostico_json = dict(diagnostico_json)

    if not parametros:
        return diagnostico_json

    mapping = {
        "anilox_lpi": ("anilox_lpi", "lpi"),
        "anilox_bcm": ("anilox_bcm", "bcm"),
        "paso_del_cilindro": ("paso_del_cilindro", "paso", "paso_cilindro"),
        "velocidad_impresion": ("velocidad_impresion", "velocidad"),
    }

    for origen, destinos in mapping.items():
        if origen not in parametros:
            continue
        valor = parametros.get(origen)
        if valor is None:
            continue

        valor_normalizado: Any = valor
        try:
            valor_float = float(valor)
        except (TypeError, ValueError):
            valor_float = None

        if valor_float is not None and math.isfinite(valor_float):
            if abs(valor_float - round(valor_float)) < 1e-6:
                valor_normalizado = int(round(valor_float))
            else:
                valor_normalizado = round(valor_float, 4)

        for destino in destinos:
            diagnostico_json[destino] = valor_normalizado

    return diagnostico_json


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
        bbox = adv.get("bbox") or adv.get("box")
        if not bbox or len(bbox) != 4:
            continue

        x0 = int(bbox[0] * scale)
        y0 = int(bbox[1] * scale)
        x1 = int(bbox[2] * scale)
        y1 = int(bbox[3] * scale)
        tipo = adv.get("tipo", "")

        descripcion = (
            (adv.get("descripcion") or adv.get("mensaje") or adv.get("etiqueta") or "")
        ).strip()
        if not descripcion:
            descripcion = DESCRIPCIONES_POR_TIPO.get(
                tipo, "Advertencia sin descripción técnica detallada."
            )

        color = colores.get(tipo, "red")
        # Rectángulo pequeño en la imagen descargable
        draw.rectangle([x0, y0, x0 + size, y0 + size], fill=color)

        advertencias_iconos.append(
            {
                "tipo": tipo,
                "pos": [x0, y0],  # compatibilidad con versiones previas
                "bbox": [x0, y0, x1, y1],
                "descripcion": descripcion,
                # Campo legado para compatibilidad con código previo
                "mensaje": descripcion,
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
            {
                "tipo": "trama_debil",
                "descripcion": "Trama débil detectada en canal negro",
                "bbox": None,
                "nivel": "medio",
            }
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


def indicadores_advertencias(advertencias: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compila estadísticas básicas de las advertencias detectadas."""

    advertencias_norm = consolidar_advertencias(advertencias)
    conteo: Counter[str] = Counter()
    total = len(advertencias_norm)

    for adv in advertencias_norm:
        tipo = (adv.get("tipo") or adv.get("type") or "").lower().strip()
        if tipo:
            conteo[tipo] += 1

    conteo_tramas = sum(
        cantidad for nombre, cantidad in conteo.items() if "trama" in nombre
    )
    conteo_texto = conteo.get("texto_pequeno", 0)
    conteo_overprint = conteo.get("overprint", 0)

    return {
        "total": total,
        "por_tipo": dict(conteo),
        "conteo_tramas": conteo_tramas,
        "conteo_texto": conteo_texto,
        "conteo_overprint": conteo_overprint,
        "hay_tramas_debiles": conteo_tramas > 0,
        "hay_texto_pequeno": conteo_texto > 0,
        "hay_overprint": conteo_overprint > 0,
    }


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
