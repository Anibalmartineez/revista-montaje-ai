"""Reglas heurísticas para clasificar el riesgo de advertencias flexográficas.

El módulo no realiza llamadas externas ni usa IA, pero se deja un parámetro
``usar_ia`` para eventuales integraciones futuras.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List

from flexo_config import get_flexo_thresholds

PT_PER_MM = 72 / 25.4


def _a_texto(diagnostico: Any) -> str:
    """Convierte el diagnóstico a un texto en minúsculas."""
    if isinstance(diagnostico, str):
        return diagnostico.lower()
    try:
        return json.dumps(diagnostico, ensure_ascii=False).lower()
    except Exception:
        return str(diagnostico).lower()


def _leer_tac(diagnostico: Any) -> float | None:
    if isinstance(diagnostico, dict):
        for clave in (
            "tac_total_v2",
            "tac_total",
            "cobertura_estimada",
            "cobertura_base_sum",
        ):
            valor = diagnostico.get(clave)
            if valor is None:
                continue
            try:
                numero = float(valor)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(numero):
                continue
            return numero
    texto = str(diagnostico).lower()
    coincidencia = re.search(r"tac[^0-9]*(\d+(?:[\.,]\d+)?)", texto)
    if not coincidencia:
        return None
    try:
        return float(coincidencia.group(1).replace(",", "."))
    except ValueError:
        return None


def _format_number(value: float, decimals: int = 2) -> str:
    text = f"{value:.{decimals}f}"
    return text.rstrip("0").rstrip(".")


def _tabla_desde_resultado_unificado(resultado: Dict[str, Any]) -> str:
    metricas = resultado.get("metricas") or {}
    umbrales = resultado.get("umbrales") or {}
    cobertura_estado = resultado.get("cobertura_estado") or {}
    tac_estado = resultado.get("tac_estado") or {}
    transferencia_estado = resultado.get("transferencia_estado") or {}
    riesgo_global = resultado.get("riesgo_global") or {}

    filas: List[Dict[str, str]] = []

    def agregar(problema: str, nivel: str, sugerencia: str) -> None:
        filas.append(
            {"problema": problema, "nivel": nivel, "sugerencia": sugerencia}
        )

    cobertura_total = metricas.get("cobertura_total")
    if cobertura_estado.get("status") == "alta" and cobertura_total is not None:
        agregar(
            f"Cobertura total alta ({_format_number(float(cobertura_total), 2)}%)",
            "🟡 Medio",
            "Controlar carga de tinta, secado y presión de impresión.",
        )
    elif cobertura_estado.get("status") == "baja" and cobertura_total is not None:
        agregar(
            f"Cobertura total baja ({_format_number(float(cobertura_total), 2)}%)",
            "🟡 Medio",
            "Verificar densidad, BCM y estabilidad de transferencia.",
        )

    tac_total = metricas.get("tac_total")
    if tac_estado.get("status") == "alto" and tac_total is not None:
        agregar(
            f"TAC alto ({_format_number(float(tac_total), 2)}%)",
            "🔴 Alto"
            if float(tac_total) >= float(umbrales.get("tac_critical") or 0)
            else "🟡 Medio",
            "Reducir carga total, optimizar separaciones y controlar secado.",
        )
    elif tac_estado.get("status") == "bajo" and tac_total is not None:
        agregar(
            f"TAC bajo ({_format_number(float(tac_total), 2)}%)",
            "🟡 Medio",
            "Revisar transferencia y densidad para evitar impresión débil.",
        )

    transferencia = transferencia_estado.get("risk") or {}
    ml_min = metricas.get("tinta_ml_min")
    if transferencia_estado.get("status") == "sobrecarga" and ml_min is not None:
        agregar(
            f"Transmisión alta ({_format_number(float(ml_min), 2)} ml/min)",
            "🔴 Alto" if int(transferencia.get("level", 1)) >= 2 else "🟡 Medio",
            "Bajar BCM o velocidad, y revisar presión/anilox.",
        )
    elif transferencia_estado.get("status") == "subcarga" and ml_min is not None:
        agregar(
            f"Transmisión baja ({_format_number(float(ml_min), 2)} ml/min)",
            "🔴 Alto" if int(transferencia.get("level", 1)) >= 2 else "🟡 Medio",
            "Subir BCM o reducir velocidad para mejorar transferencia.",
        )

    if riesgo_global.get("status") == "desbalance":
        agregar(
            "Desbalance entre carga gráfica y transferencia",
            "🔴 Alto" if int(riesgo_global.get("level", 1)) >= 2 else "🟡 Medio",
            "Ajustar parámetros de máquina para alinear TAC/cobertura con ml/min.",
        )

    if not filas:
        razones = riesgo_global.get("reasons") or []
        detalle = razones[0] if razones else "Sin riesgos detectados con las reglas establecidas."
        return f"<div id='tabla-riesgos'><p>{detalle}</p></div>"

    html_rows = "".join(
        f"<tr><td>{r['problema']}</td><td>{r['nivel']}</td><td>{r['sugerencia']}</td></tr>"
        for r in filas
    )
    return (
        "<div id='tabla-riesgos'>"
        "<table style='border-collapse:collapse; margin-top:20px; width:100%;'>"
        "<thead><tr><th>Problema detectado</th><th>Nivel de riesgo</th><th>Sugerencia</th></tr></thead>"
        f"<tbody>{html_rows}</tbody></table></div>"
    )


def simular_riesgos(
    diagnostico: str | Dict[str, Any],
    usar_ia: bool = False,
    *,
    material: str | None = None,
    anilox_lpi: float | None = None,
) -> str:
    """Evalúa reglas fijas sobre el diagnóstico dado.

    Parameters
    ----------
    diagnostico: str | dict
        Resumen estructurado del diagnóstico, puede ser texto plano o un
        diccionario con información relevante.
    usar_ia: bool, optional
        Bandera reservada para futuras integraciones con análisis por IA.

    Returns
    -------
    str
        HTML con una tabla que resume los riesgos detectados.
    """

    if isinstance(diagnostico, dict):
        resultado_unificado = diagnostico.get("resultado_diagnostico")
        if isinstance(resultado_unificado, dict):
            return _tabla_desde_resultado_unificado(resultado_unificado)

    tac_val = _leer_tac(diagnostico)
    texto = _a_texto(diagnostico)
    thresholds = get_flexo_thresholds(material=material, anilox_lpi=anilox_lpi)
    resultados: List[Dict[str, str]] = []

    def agregar(problema: str, nivel: str, sugerencia: str) -> None:
        resultados.append(
            {"problema": problema, "nivel": nivel, "sugerencia": sugerencia}
        )

    # Reglas fijas
    min_text = thresholds.min_text_pt
    min_text_str = _format_number(min_text, 2)
    texto_seguro = "no se encontraron textos menores a" not in texto
    texto_pattern = re.search(r"text[oa]s?[^0-9]*(<|menores a)\s*([0-9]+(?:[\.,][0-9]+)?)\s*pt", texto)
    texto_invalido = False
    if texto_pattern:
        try:
            valor = float(texto_pattern.group(2).replace(",", "."))
            texto_invalido = valor <= min_text + 1e-6
        except ValueError:
            texto_invalido = True
    if texto_seguro and (texto_invalido or "texto pequeño" in texto or "texto_pequeno" in texto):
        recomendado = max(min_text + 1, min_text * 1.2)
        agregar(
            f"Textos < {min_text_str} pt",
            "🔴 Alto",
            f"Aumentar a {_format_number(recomendado, 1)} pt mínimo para flexografía",
        )

    stroke_threshold = thresholds.min_stroke_mm
    stroke_str = _format_number(stroke_threshold, 2)
    stroke_pattern = re.search(
        r"traz[ao]s?[^0-9]*(<|menores a)\s*([0-9]+(?:[\.,][0-9]+)?)\s*(mm|pt)",
        texto,
    )
    stroke_invalido = False
    if stroke_pattern:
        try:
            valor = float(stroke_pattern.group(2).replace(",", "."))
            unidad = stroke_pattern.group(3)
            if unidad == "pt":
                valor = valor / PT_PER_MM
            stroke_invalido = valor <= stroke_threshold + 1e-6
        except ValueError:
            stroke_invalido = True
    if stroke_invalido or "trazo_fino" in texto:
        sugerido = max(stroke_threshold + 0.05, stroke_threshold * 1.2)
        agregar(
            f"Trazos < {stroke_str} mm",
            "🔴 Alto",
            f"Engrosar trazos a {_format_number(sugerido, 2)} mm mínimo",
        )

    resolucion_pattern = re.search(
        r"resoluci[óo]n[^0-9]*([0-9]+(?:[\.,][0-9]+)?)\s*dpi",
        texto,
    )
    resolucion_baja = False
    if resolucion_pattern:
        try:
            valor = float(resolucion_pattern.group(1).replace(",", "."))
            resolucion_baja = valor < thresholds.min_resolution_dpi - 1e-6
        except ValueError:
            resolucion_baja = True
    if resolucion_baja:
        agregar(
            f"Resolución < {thresholds.min_resolution_dpi} dpi",
            "🟡 Medio",
            f"Incrementar la resolución de imágenes a {thresholds.min_resolution_dpi} dpi",
        )

    if "rgb" in texto or ("pantone" in texto and "sin nombre" in texto):
        agregar(
            "Elementos fuera de CMYK",
            "🟡 Medio",
            "Convertir a CMYK antes de exportar PDF",
        )

    if "overprint" in texto or "sobreimpresi" in texto:
        agregar(
            "Sobreimpresión activa",
            "🔴 Alto",
            "Revisar configuraciones de sobreimpresión",
        )

    if tac_val is None:
        tac_val = _leer_tac(texto)
    if tac_val is not None:
        if tac_val > thresholds.tac_critical:
            agregar(
                f"TAC > {thresholds.tac_critical}%",
                "🔴 Alto",
                "Reducir cobertura total de tinta",
            )
        elif thresholds.tac_warning <= tac_val <= thresholds.tac_critical:
            agregar(
                f"TAC {thresholds.tac_warning}% - {thresholds.tac_critical}%",
                "🟡 Medio",
                "Optimizar separaciones para bajar TAC",
            )

    borde_pattern = re.search(
        r"([0-9]+(?:[\.,][0-9]+)?)\s*mm[^a-z]*(borde|margen)",
        texto,
    )
    borde_cercano = False
    if borde_pattern:
        try:
            distancia = float(borde_pattern.group(1).replace(",", "."))
            borde_cercano = distancia <= thresholds.edge_distance_mm + 1e-6
        except ValueError:
            borde_cercano = True
    if borde_cercano:
        agregar(
            f"Elementos < {_format_number(thresholds.edge_distance_mm, 1)} mm del borde",
            "🟡 Medio",
            f"Aumentar margen de seguridad a {_format_number(thresholds.edge_distance_mm, 1)} mm",
        )

    if "sin sangrado" in texto or ("no se detect" in texto and "sangrado" in texto):
        agregar(
            "Sin sangrado",
            "🟡 Medio",
            f"Agregar {_format_number(thresholds.min_bleed_mm, 1)} mm de sangrado",
        )

    if "contraste débil" in texto or "contraste debil" in texto:
        agregar(
            "Contraste débil",
            "🟡 Medio",
            "Revisar contraste de elementos",
        )

    if not resultados:
        return (
            "<div id='tabla-riesgos'><p>Sin riesgos detectados con las reglas establecidas.</p></div>"
        )

    filas = "".join(
        f"<tr><td>{r['problema']}</td><td>{r['nivel']}</td><td>{r['sugerencia']}</td></tr>"
        for r in resultados
    )
    tabla = (
        "<div id='tabla-riesgos'>"
        "<table style='border-collapse:collapse; margin-top:20px; width:100%;'>"
        "<thead><tr><th>Problema detectado</th><th>Nivel de riesgo</th><th>Sugerencia</th></tr></thead>"
        f"<tbody>{filas}</tbody></table></div>"
    )
    return tabla
