"""Tests para utilidades de diagnostico flexográfico."""

import fitz
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagnostico_flexo import (
    calcular_cobertura_y_tac,
    resumen_advertencias,
    semaforo_riesgo,
)


def test_calcular_cobertura_y_tac(tmp_path):
    """La cobertura por canal refleja los porcentajes reales y el TAC p95."""

    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(0, 0, page.rect.width / 2, page.rect.height)
    # Mitad de la página con tinta negra
    page.draw_rect(rect, color=(0, 0, 0, 1), fill=(0, 0, 0, 1))
    pdf_path = tmp_path / "ejemplo.pdf"
    doc.save(pdf_path)
    doc.close()

    coberturas, tac_p95 = calcular_cobertura_y_tac(str(pdf_path))
    assert 40 < coberturas["Negro"] < 60
    assert (
        coberturas["Cyan"] < 1
        and coberturas["Magenta"] < 1
        and coberturas["Amarillo"] < 1
    )
    assert 95 <= tac_p95 <= 100


def test_calcular_cobertura_ignora_casi_blancos(tmp_path):
    """Los píxeles casi blancos no aportan cobertura."""

    doc = fitz.open()
    page = doc.new_page()
    # Toda la página en un tono muy cercano al blanco
    page.draw_rect(page.rect, fill=(0.98, 0.98, 0.98))
    pdf_path = tmp_path / "casi_blanco.pdf"
    doc.save(pdf_path)
    doc.close()

    coberturas, tac_p95 = calcular_cobertura_y_tac(str(pdf_path))
    assert all(v < 1 for v in coberturas.values())
    assert tac_p95 < 1


def test_resumen_y_semaforo():
    advertencias = [
        {"nivel": "critico"},
        {"nivel": "medio"},
        {"nivel": "medio"},
        {"nivel": "leve"},
    ]

    resumen = resumen_advertencias(advertencias)
    assert "4 advertencias" in resumen
    assert "1 críticas" in resumen
    assert "2 medias" in resumen
    assert "1 leves" in resumen
    assert semaforo_riesgo(advertencias) == "🔴"


def test_resumen_sin_advertencias():
    assert resumen_advertencias([]).startswith("✅ Archivo sin riesgos")
    assert semaforo_riesgo([]) == "🟢"
