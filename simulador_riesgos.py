"""Simulador de riesgos para diagnóstico flexográfico.

Este módulo aplica reglas fijas para clasificar el nivel de riesgo de
advertencias detectadas en un diagnóstico flexográfico. No utiliza IA ni
requiere conexión externa, aunque se deja un parámetro ``usar_ia`` para una
posible integración futura.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def _a_texto(diagnostico: Any) -> str:
    """Convierte el diagnóstico a un texto en minúsculas."""
    if isinstance(diagnostico, str):
        return diagnostico.lower()
    try:
        return json.dumps(diagnostico, ensure_ascii=False).lower()
    except Exception:
        return str(diagnostico).lower()


def simular_riesgos(diagnostico: str | Dict[str, Any], usar_ia: bool = False) -> str:
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

    texto = _a_texto(diagnostico)
    resultados: List[Dict[str, str]] = []

    def agregar(problema: str, nivel: str, sugerencia: str) -> None:
        resultados.append(
            {"problema": problema, "nivel": nivel, "sugerencia": sugerencia}
        )

    # Reglas fijas
    texto_seguro = "no se encontraron textos menores a 4 pt" not in texto
    if texto_seguro and (
        re.search(r"text[oa]s?\s*(<|menores a)\s*4\s*pt", texto)
        or "texto pequeño" in texto
    ):
        agregar("Textos < 4 pt", "🔴 Alto", "Aumentar a 5 pt mínimo para flexografía")

    if re.search(r"traz[ao]s?\s*(<|menores a)\s*0\.25\s*pt", texto) or "trazo_fino" in texto:
        agregar("Trazos < 0.25 pt", "🔴 Alto", "Engrosar trazos a 0.30 pt mínimo")

    if re.search(r"resoluci[óo]n.*<\s*300\s*dpi", texto):
        agregar(
            "Resolución < 300 dpi",
            "🟡 Medio",
            "Incrementar la resolución de imágenes a 300 dpi",
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

    m_tac = re.search(r"tac[^0-9]*(\d+)", texto)
    if m_tac:
        tac_val = int(m_tac.group(1))
        if tac_val > 320:
            agregar("TAC > 320%", "🔴 Alto", "Reducir cobertura total de tinta")
        elif 280 <= tac_val <= 320:
            agregar("TAC 280%-320%", "🟡 Medio", "Optimizar separaciones para bajar TAC")

    if "2 mm" in texto and ("borde" in texto or "margen" in texto):
        agregar(
            "Elementos < 2 mm del borde",
            "🟡 Medio",
            "Aumentar margen de seguridad a 2 mm",
        )

    if "sin sangrado" in texto or "no se detect" in texto and "sangrado" in texto:
        agregar("Sin sangrado", "🟡 Medio", "Agregar 3 mm de sangrado")

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
