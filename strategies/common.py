from __future__ import annotations

from typing import Any, Dict, Tuple

from montaje_offset_inteligente import MontajeConfig


def build_call_args(config: MontajeConfig) -> Tuple[float, float, Dict[str, Any]]:
    """Prepara argumentos comunes para ``montar_pliego_offset_inteligente``."""

    ancho_pliego, alto_pliego = config.tamano_pliego
    sangrado = config.sangrado if config.sangrado is not None else 0.0
    separacion = config.separacion if config.separacion is not None else 4.0

    filas = config.filas_grilla if config.filas_grilla is not None else 0
    columnas = config.columnas_grilla if config.columnas_grilla is not None else 0
    celda_ancho = config.ancho_grilla_mm if config.ancho_grilla_mm is not None else 0.0
    celda_alto = config.alto_grilla_mm if config.alto_grilla_mm is not None else 0.0

    marcas_registro = config.marcas_registro or config.agregar_marcas
    marcas_corte = config.marcas_corte or config.agregar_marcas

    kwargs: Dict[str, Any] = {
        "separacion": separacion,
        "sangrado": sangrado,
        "usar_trimbox": config.usar_trimbox,
        "ordenar_tamano": config.ordenar_tamano,
        "permitir_rotacion": config.permitir_rotacion,
        "alinear_filas": config.alinear_filas,
        "preferir_horizontal": config.pref_orientacion_horizontal,
        "centrar": config.centrar,
        "debug_grilla": config.debug_grilla,
        "espaciado_horizontal": config.espaciado_horizontal,
        "espaciado_vertical": config.espaciado_vertical,
        "margen_izq": config.margen_izquierdo,
        "margen_der": config.margen_derecho,
        "margen_sup": config.margen_superior,
        "margen_inf": config.margen_inferior,
        "filas": filas,
        "columnas": columnas,
        "celda_ancho": celda_ancho,
        "celda_alto": celda_alto,
        "pinza_mm": config.pinza_mm,
        "lateral_mm": config.lateral_mm,
        "marcas_registro": marcas_registro,
        "marcas_corte": marcas_corte,
        "cutmarks_por_forma": config.cutmarks_por_forma,
        "export_area_util": config.export_area_util,
        "preview_only": not config.es_pdf_final,
        "output_path": config.output_path,
        "preview_path": config.preview_path,
        "posiciones_manual": config.posiciones_manual,
        "devolver_posiciones": config.devolver_posiciones,
        "resumen_path": config.resumen_path,
        "export_compat": config.export_compat,
    }

    return float(ancho_pliego), float(alto_pliego), kwargs
