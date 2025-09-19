"""Tests para utilidades de diagnostico flexográfico."""

import fitz
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cobertura_utils import calcular_metricas_cobertura
from diagnostico_flexo import (
    resumen_advertencias,
    semaforo_riesgo,
    coeficiente_material,
    obtener_coeficientes_material,
)
from montaje_flexo import detectar_tramas_débiles
from simulador_riesgos import simular_riesgos


def test_calcular_metricas_cobertura(tmp_path):
    """La cobertura por canal refleja los porcentajes reales y el TAC p95."""

    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(0, 0, page.rect.width / 2, page.rect.height)
    # Mitad de la página con tinta negra
    page.draw_rect(rect, color=(0, 0, 0, 1), fill=(0, 0, 0, 1))
    pdf_path = tmp_path / "ejemplo.pdf"
    doc.save(pdf_path)
    doc.close()

    metricas = calcular_metricas_cobertura(str(pdf_path))
    coberturas = metricas["cobertura_promedio"]
    assert 40 < coberturas["Negro"] < 60
    assert (
        coberturas["Cyan"] < 1
        and coberturas["Magenta"] < 1
        and coberturas["Amarillo"] < 1
    )
    assert 95 <= metricas["tac_p95"] <= 100


def test_calcular_cobertura_ignora_casi_blancos(tmp_path):
    """Los píxeles casi blancos no aportan cobertura."""

    doc = fitz.open()
    page = doc.new_page()
    # Toda la página en un tono muy cercano al blanco
    page.draw_rect(page.rect, fill=(0.98, 0.98, 0.98))
    pdf_path = tmp_path / "casi_blanco.pdf"
    doc.save(pdf_path)
    doc.close()

    metricas = calcular_metricas_cobertura(str(pdf_path))
    coberturas = metricas["cobertura_promedio"]
    assert all(v < 1 for v in coberturas.values())
    assert metricas["tac_p95"] < 1


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


def test_tramas_debiles_no_false_positive(tmp_path, monkeypatch):
    """Una página en blanco no debe reportar tramas débiles."""

    from PIL import Image

    def fake_convert_from_path(path_pdf, dpi=300, first_page=1, last_page=1):
        """Devuelve una imagen CMYK vacía evitando depender de poppler."""
        return [Image.new("CMYK", (100, 100), color=(0, 0, 0, 0))]

    # Simula pdf2image para no requerir poppler en los tests
    monkeypatch.setattr("montaje_flexo.convert_from_path", fake_convert_from_path)

    doc = fitz.open()
    doc.new_page()
    pdf_path = tmp_path / "blanco.pdf"
    doc.save(pdf_path)
    doc.close()

    advertencias = detectar_tramas_débiles(str(pdf_path))

    # Soporta tanto respuestas en texto como diccionarios de advertencias
    mensajes = [a if isinstance(a, str) else a.get("mensaje", "") for a in advertencias]

    assert any("No se detectaron tramas débiles" in m for m in mensajes)
    assert not any("Trama muy débil" in m for m in mensajes)


def test_simulador_riesgos_ignora_texto_negado():
    """La frase de negación no debe activar el riesgo de textos pequeños."""

    resumen = "✔️ No se encontraron textos menores a 4 pt."
    html = simular_riesgos(resumen)
    assert "Textos < 4 pt" not in html


def test_coeficiente_material_usa_json():
    """Los coeficientes de materiales se obtienen desde el JSON compartido."""

    coefs = obtener_coeficientes_material()
    assert coefs, "Se esperaba un mapa de coeficientes cargado desde data/material_coefficients.json"
    film = coefs.get("film")
    carton = coefs.get("carton")
    default_val = coefs.get("default")

    if film is not None:
        assert coeficiente_material("Film") == film
    if carton is not None:
        assert coeficiente_material("cartón") == carton

    if default_val is not None:
        assert coeficiente_material("material desconocido") == default_val

    override = coeficiente_material("material sin registrar", default=0.71)
    assert override == 0.71
