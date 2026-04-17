import json
import math
import os
import unicodedata
from collections import Counter
from functools import lru_cache
from typing import Any, Dict, List, Mapping

import fitz
import numpy as np
from flask import current_app
from PIL import Image, ImageDraw

from flexo_config import FlexoThresholds, get_flexo_thresholds
from tinta_utils import (
    clasificar_riesgo_por_ideal,
    get_ink_ideal_mlmin,
    normalizar_coberturas,
)


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


_BASE_DIR = os.path.dirname(__file__)
_COEFICIENTES_PATH = os.path.join(_BASE_DIR, "data", "material_coefficients.json")


def _normalizar_clave_material(nombre: str) -> str:
    """Normaliza un nombre de material para usarlo como clave."""

    if not nombre:
        return ""
    texto = unicodedata.normalize("NFKD", str(nombre))
    sin_tildes = "".join(ch for ch in texto if not unicodedata.combining(ch))
    filtrado = "".join(
        ch for ch in sin_tildes.lower() if ch.isalnum() or ch in {" ", "_"}
    )
    return filtrado.strip().replace(" ", "_")


@lru_cache(maxsize=1)
def _cargar_coeficientes_material() -> dict[str, float]:
    """Lee desde disco los coeficientes de absorción/transmisión."""

    try:
        with open(_COEFICIENTES_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

    coeficientes: dict[str, float] = {}
    for clave, valor in (data or {}).items():
        try:
            coef = float(valor)
        except (TypeError, ValueError):
            continue
        coeficientes[_normalizar_clave_material(clave)] = coef
    return coeficientes


def obtener_coeficientes_material() -> dict[str, float]:
    """Devuelve una copia del mapeo de coeficientes configurado."""

    return dict(_cargar_coeficientes_material())


def coeficiente_material(material: str, *, default: float | None = None) -> float | None:
    """Obtiene el coeficiente de transmisión configurado para ``material``.

    Si no existe un coeficiente específico, se retorna ``default`` (si se
    proporcionó) o el valor definido como ``default`` en el JSON, cuando esté
    disponible.
    """

    coeficientes = _cargar_coeficientes_material()
    if not coeficientes:
        return default

    clave = _normalizar_clave_material(material)
    if clave and clave in coeficientes:
        return coeficientes[clave]

    if default is not None:
        return default

    return coeficientes.get("default")


def tac_desde_cobertura(cobertura: Mapping[str, Any] | None) -> float:
    """Calcula el TAC como la suma normalizada de los canales CMYK.

    La suma se basa en ``tinta_utils.normalizar_coberturas`` para reutilizar la
    lógica de recorte 0–100% por canal que emplea el pipeline v2.  El resultado
    se redondea a dos decimales, igual que ``tac_total_v2``.
    """

    valores = normalizar_coberturas(cobertura)
    total = sum(valores.get(canal, 0.0) for canal in ("C", "M", "Y", "K"))
    return round(total, 2)


def evaluar_riesgo_tinta(material: str | None, ml_min: float | None) -> Dict[str, Any]:
    """Clasifica el riesgo de tinta reutilizando las utilidades centrales."""

    ideal = get_ink_ideal_mlmin(material)
    nivel, etiqueta, razones = clasificar_riesgo_por_ideal(ml_min, ideal)
    return {"level": nivel, "label": etiqueta, "reasons": list(razones)}


def _as_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numero = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero):
        return None
    return numero


def construir_resultado_diagnostico(
    diagnostico_json: Dict[str, Any] | None,
    *,
    advertencias_resumen: str | None = None,
    indicadores_advertencias: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Genera una fuente única de verdad para métricas e interpretación flexo."""

    dj = dict(diagnostico_json or {})
    material = (dj.get("material") or "").strip()
    anilox_lpi = _as_number(dj.get("anilox_lpi") or dj.get("lpi"))
    anilox_bcm = _as_number(dj.get("anilox_bcm") or dj.get("bcm"))
    velocidad = _as_number(dj.get("velocidad_impresion") or dj.get("velocidad"))
    paso = _as_number(
        dj.get("paso_del_cilindro") or dj.get("paso_cilindro") or dj.get("paso")
    )
    ancho_mm = _as_number(dj.get("ancho_mm"))
    alto_mm = _as_number(dj.get("alto_mm"))
    cobertura_total = _as_number(dj.get("cobertura_total"))
    cobertura_por_canal = normalizar_coberturas(
        dj.get("cobertura_por_canal") or dj.get("cobertura")
    )
    indicadores = dict(indicadores_advertencias or {})
    overprint_count = int(indicadores.get("conteo_overprint") or 0)
    overprint_detected = bool(indicadores.get("hay_overprint") or overprint_count > 0)
    dominant_channel = None
    dominant_channel_value = None
    if cobertura_por_canal:
        dominant_channel, dominant_channel_value = max(
            cobertura_por_canal.items(),
            key=lambda item: item[1],
        )

    tac_total = _as_number(dj.get("tac_total_v2"))
    if tac_total is None:
        tac_total = _as_number(dj.get("tac_total"))
    if tac_total is None and cobertura_por_canal:
        tac_total = tac_desde_cobertura(cobertura_por_canal)
    if tac_total is not None:
        tac_total = round(tac_total, 2)

    ml_min = _as_number(dj.get("tinta_ml_min"))
    ml_min_ideal = _as_number(dj.get("tinta_ideal_ml_min"))
    if ml_min_ideal is None and material:
        ml_min_ideal = get_ink_ideal_mlmin(material)

    thresholds = obtener_thresholds_flexo(material=material, anilox_lpi=anilox_lpi)
    coverage_high = 85.0
    coverage_low = 10.0
    tac_low = round(max(80.0, thresholds.tac_warning * 0.45), 2)

    coverage_status = "sin_datos"
    coverage_reasons: List[str] = []
    if cobertura_total is not None:
        cobertura_total = round(cobertura_total, 2)
        if cobertura_total >= coverage_high:
            coverage_status = "alta"
            coverage_reasons.append(
                f"Cobertura total alta ({cobertura_total:.2f}%). Tendencia a sobrecarga."
            )
        elif cobertura_total <= coverage_low:
            coverage_status = "baja"
            coverage_reasons.append(
                f"Cobertura total baja ({cobertura_total:.2f}%). Tendencia a subcarga."
            )
        else:
            coverage_status = "normal"
            coverage_reasons.append(
                f"Cobertura total dentro de rango operativo ({cobertura_total:.2f}%)."
            )

    tac_status = "sin_datos"
    tac_reasons: List[str] = []
    if tac_total is not None:
        if tac_total >= thresholds.tac_critical:
            tac_status = "alto"
            tac_reasons.append(
                f"TAC alto ({tac_total:.2f}%) sobre el límite crítico {thresholds.tac_critical}%."
            )
        elif tac_total >= thresholds.tac_warning:
            tac_status = "alto"
            tac_reasons.append(
                f"TAC elevado ({tac_total:.2f}%) sobre el límite recomendado {thresholds.tac_warning}%."
            )
        elif tac_total <= tac_low:
            if cobertura_total is not None and cobertura_total >= coverage_high:
                tac_status = "normal"
                tac_reasons.append(
                    f"TAC moderado ({tac_total:.2f}%) con cobertura total alta ({cobertura_total:.2f}%). No se interpreta como TAC bajo por posible predominio de un canal."
                )
            else:
                tac_status = "bajo"
                tac_reasons.append(
                    f"TAC bajo ({tac_total:.2f}%). Riesgo de impresión débil."
                )
        else:
            tac_status = "normal"
            tac_reasons.append(f"TAC dentro de rango operativo ({tac_total:.2f}%).")

    transferencia_riesgo = evaluar_riesgo_tinta(material, ml_min)
    ink_level = int(transferencia_riesgo.get("level", 1))
    if ml_min is None or ml_min_ideal is None or ml_min_ideal <= 0:
        transferencia_status = "sin_datos"
    elif ink_level == 0:
        transferencia_status = "equilibrada"
    elif ml_min < ml_min_ideal:
        transferencia_status = "subcarga"
    else:
        transferencia_status = "sobrecarga"

    demanda_alta = coverage_status == "alta" or tac_status == "alto"
    demanda_baja = coverage_status == "baja" or tac_status == "bajo"
    tinta_alta = transferencia_status == "sobrecarga"
    tinta_baja = transferencia_status == "subcarga"

    global_status = "estable"
    global_level = 0
    global_label = "Verde"
    global_reasons: List[str] = []

    if demanda_alta and tinta_baja:
        global_status = "desbalance"
        global_level = 2 if ink_level >= 1 else 1
        global_label = "Rojo" if global_level == 2 else "Amarillo"
        global_reasons.append(
            "Carga gráfica alta con transferencia de tinta por debajo del ideal."
        )
    elif demanda_alta and tinta_alta:
        global_status = "sobrecarga"
        global_level = 2
        global_label = "Rojo"
        global_reasons.append(
            "Cobertura/TAC altos y transmisión alta: riesgo claro de sobrecarga."
        )
    elif demanda_alta:
        global_status = "sobrecarga"
        global_level = 1 if tac_status == "alto" else 0
        global_label = "Amarillo" if global_level else "Verde"
        global_reasons.append(
            "Carga gráfica alta. Mantener control estricto de tinta y secado."
        )
    elif demanda_baja and tinta_baja:
        global_status = "subcarga"
        global_level = 2 if ink_level >= 1 else 1
        global_label = "Rojo" if global_level == 2 else "Amarillo"
        global_reasons.append(
            "Carga gráfica baja y transmisión baja: riesgo de impresión débil."
        )
    elif demanda_baja:
        global_status = "subcarga"
        global_level = 1
        global_label = "Amarillo"
        global_reasons.append(
            "Carga gráfica baja. Revisar densidad y soporte antes de imprimir."
        )
    elif tinta_alta:
        global_status = "sobrecarga"
        global_level = 1 if ink_level == 1 else 2
        global_label = "Amarillo" if global_level == 1 else "Rojo"
        global_reasons.append(
            "Transmisión de tinta por encima del ideal."
        )
    elif tinta_baja:
        global_status = "subcarga"
        global_level = 1 if ink_level == 1 else 2
        global_label = "Amarillo" if global_level == 1 else "Rojo"
        global_reasons.append(
            "Transmisión de tinta por debajo del ideal."
        )
    else:
        global_reasons.append("Cobertura, TAC y transmisión alineados entre sí.")

    for grupo in (
        coverage_reasons,
        tac_reasons,
        list(transferencia_riesgo.get("reasons") or []),
    ):
        for reason in grupo:
            if reason and reason not in global_reasons:
                global_reasons.append(reason)

    if advertencias_resumen:
        global_reasons.append(str(advertencias_resumen))

    return {
        "metricas": {
            "material": material or None,
            "anilox_lpi": anilox_lpi,
            "anilox_bcm": anilox_bcm,
            "velocidad_impresion": velocidad,
            "paso_cilindro": paso,
            "ancho_mm": ancho_mm,
            "alto_mm": alto_mm,
            "cobertura_total": cobertura_total,
            "tac_total": tac_total,
            "tinta_ml_min": ml_min,
            "tinta_ideal_ml_min": ml_min_ideal,
            "cobertura_por_canal": cobertura_por_canal or None,
            "canal_dominante": dominant_channel,
            "canal_dominante_valor": dominant_channel_value,
        },
        "umbrales": {
            "coverage_low": coverage_low,
            "coverage_high": coverage_high,
            "tac_low": tac_low,
            "tac_warning": thresholds.tac_warning,
            "tac_critical": thresholds.tac_critical,
        },
        "cobertura_estado": {
            "status": coverage_status,
            "reasons": coverage_reasons,
        },
        "tac_estado": {
            "status": tac_status,
            "reasons": tac_reasons,
        },
        "transferencia_estado": {
            "status": transferencia_status,
            "risk": transferencia_riesgo,
        },
        "riesgo_global": {
            "status": global_status,
            "level": global_level,
            "label": global_label,
            "reasons": global_reasons,
        },
        "advertencias": {
            "resumen": advertencias_resumen or "",
            "indicadores": dict(indicadores_advertencias or {}),
            "sobreimpresion": {
                "detectada": overprint_detected,
                "conteo": overprint_count,
            },
        },
    }


def obtener_thresholds_flexo(
    material: str | None = None, anilox_lpi: float | None = None
) -> FlexoThresholds:
    """Proxy directo a ``flexo_config.get_flexo_thresholds`` sin valores propios."""

    return get_flexo_thresholds(material=material, anilox_lpi=anilox_lpi)


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
