from __future__ import annotations

from typing import Any, Dict, List

from flexo_config import get_flexo_thresholds


def _card(titulo: str, items_html: List[str] | str) -> str:
    """Envuelve una lista de elementos en un contenedor con título."""
    if isinstance(items_html, list):
        items = "".join(items_html)
    else:
        items = items_html
    return f"<div class='card'><h3>{titulo}</h3><ul>{items}</ul></div>"


def resumen_cobertura_tac(metricas: Dict[str, Any], material: str) -> List[str]:
    """Genera una lista de ítems HTML con TAC y cobertura por canal."""

    items: List[str] = []
    tac_p95 = metricas["tac_p95"]
    tac_max = metricas["tac_max"]
    thresholds = get_flexo_thresholds(material=material)
    warn_lim = thresholds.tac_warning
    crit_lim = thresholds.tac_critical

    if tac_p95 <= warn_lim:
        estado = "ok"
    elif tac_p95 <= crit_lim:
        estado = "warn"
    else:
        estado = "error"
    icon = {"ok": "✔️", "warn": "⚠️", "error": "❌"}[estado]
    items.append(
        (
            f"<li><span class='icono {estado}'>{icon}</span> TAC p95: "
            f"<b>{tac_p95:.0f}%</b> (límite sugerido {crit_lim}%). TAC máx: "
            f"<b>{tac_max:.0f}%</b>.</li>"
        )
    )
    for canal, area in metricas["cobertura_por_area"].items():
        nombre = canal if canal != "Cyan" else "Cian"
        items.append(f"<li>Área con {nombre}: <b>{area:.1f}%</b></li>")
    return items


def generar_reporte_tecnico(datos_analisis: Dict[str, Any]) -> str:
    """Construye el reporte técnico HTML a partir de los datos de análisis.

    Parameters
    ----------
    datos_analisis: Dict[str, Any]
        Diccionario con listas o datos necesarios para cada sección del reporte.
    Returns
    -------
    str
        Fragmento HTML con el diagnóstico completo.
    """
    secciones: List[str] = []

    if datos_analisis.get("diseno_info"):
        secciones.append(_card("📐 Diseño", datos_analisis["diseno_info"]))
    if datos_analisis.get("montaje_info"):
        secciones.append(_card("🧱 Montaje", datos_analisis["montaje_info"]))
    if datos_analisis.get("cobertura_info"):
        secciones.append(_card("🖨️ Cobertura y tinta", datos_analisis["cobertura_info"]))
    if datos_analisis.get("riesgos_info"):
        secciones.append(_card("⚠️ Advertencias", datos_analisis["riesgos_info"]))
    if datos_analisis.get("resolucion_items"):
        secciones.append(_card("🖼️ Resolución de imágenes", datos_analisis["resolucion_items"]))
    if datos_analisis.get("til_items"):
        secciones.append(_card("🧮 TAC y cobertura por canal", datos_analisis["til_items"]))
    if datos_analisis.get("capas_items"):
        secciones.append(_card("🎯 Capas especiales (White/Varnish/Troquel)", datos_analisis["capas_items"]))
    if datos_analisis.get("diagnostico_material"):
        secciones.append(_card("🧪 Diagnóstico por material", datos_analisis["diagnostico_material"]))

    tinta = datos_analisis.get("tinta")
    if tinta:
        if tinta.get("error"):
            secciones.append(
                "<div class='card'><h3>💧 Simulación de tinta</h3>"
                f"<p>Error en la simulación: {tinta['error']}</p></div>"
            )
        else:
            barra_pct = tinta.get("barra_pct", 0)
            barra_html = (
                "<div style='background:#ddd;border-radius:4px;width:100%;height:10px;'>"
                f"<div style='background:#0056b3;width:{barra_pct}%;height:100%;'></div></div>"
            )
            secciones.append(
                "<div class='card'><h3>💧 Simulación de tinta</h3>"
                f"<p>Cantidad estimada de tinta transferida: <b>{tinta.get('tinta_ml')} ml/min</b></p>"
                f"<img src='data:image/png;base64,{tinta.get('imagen', '')}' alt='Vista previa de tinta' "
                "style='max-width:100%; height:auto; margin-top:10px;'>"
                f"{barra_html}"
                f"<p>{tinta.get('advertencia', '')}</p>"
                "</div>"
            )

    return "<div class='diagnostico'>" + "".join(secciones) + "</div>"


__all__ = ["generar_reporte_tecnico", "resumen_cobertura_tac"]
