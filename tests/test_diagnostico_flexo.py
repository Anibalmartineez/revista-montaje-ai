"""Tests para utilidades de diagnostico flexográfico."""

import fitz
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from advertencias_disenio import verificar_lineas_finas_v2, verificar_textos_pequenos
from contextlib import contextmanager
from pathlib import Path

import fitz
import pytest
from flask import Flask, template_rendered

from cobertura_utils import calcular_metricas_cobertura
from diagnostico_flexo import (
    generar_preview_diagnostico,
    indicadores_advertencias,
    resumen_advertencias,
    semaforo_riesgo,
    coeficiente_material,
    obtener_coeficientes_material,
)
from flexo_config import FlexoThresholds, get_flexo_thresholds
from tinta_utils import InkParams, calcular_transmision_tinta
from montaje_flexo import detectar_tramas_débiles
from advertencias_disenio import (
    revisar_sangrado,
    verificar_lineas_finas_v2,
    verificar_textos_pequenos,
)
from simulador_riesgos import simular_riesgos


@contextmanager
def capture_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def _make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.draw_rect(page.rect, fill=(1, 1, 1))
    doc.save(path)
    doc.close()


def _setup_revision_app(
    tmp_path,
    monkeypatch,
    use_flag,
    tac_v2,
    tac_legacy,
    *,
    diag_json_override=None,
    cobertura_override=None,
):
    import routes

    static_dir = tmp_path / "static"
    uploads_dir = static_dir / "uploads"
    simul_dir = static_dir / "simulaciones"
    iconos_path = uploads_dir / "iconos.png"
    overlay_path = tmp_path / "overlay.png"
    base_img = tmp_path / "base.png"

    uploads_dir.mkdir(parents=True, exist_ok=True)
    simul_dir.mkdir(parents=True, exist_ok=True)
    iconos_path.write_bytes(b"iconos")
    overlay_path.write_bytes(b"overlay")
    base_img.write_bytes(b"base")

    cobertura_por_canal = cobertura_override or {
        "Cian": 70.1,
        "Magenta": 65.2,
        "Amarillo": 55.3,
        "Negro": 45.4,
    }
    cobertura_letras = {
        "C": cobertura_por_canal.get("Cian", 0.0),
        "M": cobertura_por_canal.get("Magenta", 0.0),
        "Y": cobertura_por_canal.get("Amarillo", 0.0),
        "K": cobertura_por_canal.get("Negro", 0.0),
    }

    def fake_revisar(
        path_pdf,
        anilox_lpi,
        paso_mm,
        material_norm,
        anilox_bcm,
        velocidad_impresion,
        cobertura_estimada,
    ):
        tac_total_v2 = tac_v2 if tac_v2 is not None else round(sum(cobertura_letras.values()), 2)
        diag_json = {
            "tac_total_v2": tac_total_v2,
            "tac_total": tac_legacy if tac_legacy is not None else tac_total_v2,
            "cobertura_por_canal": cobertura_letras,
        }
        if diag_json_override:
            diag_json.update(diag_json_override)

        analisis = {
            "tramas_debiles": [],
            "cobertura_por_canal": cobertura_por_canal,
            "textos_pequenos": [],
            "resolucion_minima": 0,
            "trama_minima": 5,
            "cobertura_total": 83.2,
            "tac_total": tac_legacy,
            "tac_total_v2": tac_total_v2,
            "tac_p95": 310.0,
            "tac_max": 335.7,
            "diagnostico_json": diag_json,
        }
        return ("<div>Resumen</div>", None, "Diagnóstico", analisis, [])

    def fake_analizar(path_pdf, advertencias):
        return {"overlay_path": str(overlay_path), "advertencias": [], "dpi": 150}

    def fake_preview(path_pdf, advertencias, dpi=150):
        base_rel = "uploads/base.png"
        base_rel_path = static_dir / base_rel
        base_rel_path.parent.mkdir(parents=True, exist_ok=True)
        base_rel_path.write_bytes(b"base-preview")
        return (str(base_img), base_rel, "uploads/iconos.png", [])

    def fake_simulacion(base_path, advertencias, lpi, output_path):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"sim")

    def fake_riesgos(resumen):
        return "<div class='riesgo'></div>"

    monkeypatch.setattr(routes, "revisar_diseño_flexo", fake_revisar)
    monkeypatch.setattr(routes, "analizar_riesgos_pdf", fake_analizar)
    monkeypatch.setattr(routes, "generar_preview_diagnostico", fake_preview)
    monkeypatch.setattr(routes, "generar_simulacion_avanzada", fake_simulacion)
    monkeypatch.setattr(routes, "simular_riesgos", fake_riesgos)

    template_dir = Path(__file__).resolve().parents[1] / "templates"
    app = Flask(__name__, static_folder=str(static_dir), template_folder=str(template_dir))
    app.config.update(
        TESTING=True,
        SECRET_KEY="test",
        USE_PIPELINE_V2=use_flag,
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
    )
    app.register_blueprint(routes.routes_bp)
    app.add_url_rule(
        "/revision",
        endpoint="revision",
        view_func=app.view_functions["routes.revision"],
    )

    try:
        from flask import current_app as _current_app

        _ = _current_app

        try:
            routes.current_app.config.setdefault(
                "USE_PIPELINE_V2", True if use_flag else False
            )
        except Exception:
            pass

        if hasattr(routes, "app") and getattr(routes.app, "jinja_env", None):
            routes.app.config.setdefault("USE_PIPELINE_V2", True if use_flag else False)
            routes.app.jinja_env.globals.setdefault(
                "USE_PIPELINE_V2", True if use_flag else False
            )
    except Exception:
        pass

    app.jinja_env.globals.setdefault("USE_PIPELINE_V2", True if use_flag else False)
    return app


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

    resultado = detectar_tramas_débiles(str(pdf_path))

    mensajes = resultado["mensajes"]

    assert any("No se detectaron tramas débiles" in m for m in mensajes)
    assert not any("Trama muy débil" in m for m in mensajes)
    assert resultado["advertencias"] == []
    assert resultado["hay_tramas_debiles"] is False


def test_tramas_debiles_activa_indicador(tmp_path, monkeypatch):
    """Una trama débil en el canal negro se refleja en los indicadores globales."""

    import numpy as np
    from PIL import Image

    def fake_convert_from_path(path_pdf, dpi=300, first_page=1, last_page=1):
        data = np.zeros((50, 50, 4), dtype=np.uint8)
        data[:, :, 3] = 10  # Canal K con cobertura muy baja pero presente
        imagen = Image.fromarray(data, mode="CMYK")
        return [imagen]

    monkeypatch.setattr("montaje_flexo.convert_from_path", fake_convert_from_path)

    doc = fitz.open()
    doc.new_page()
    pdf_path = tmp_path / "trama_debil.pdf"
    doc.save(pdf_path)
    doc.close()

    resultado = detectar_tramas_débiles(str(pdf_path))

    assert resultado["hay_tramas_debiles"] is True
    assert any("Trama muy débil" in m for m in resultado["mensajes"])
    stats = indicadores_advertencias(resultado["advertencias"])
    assert stats["hay_tramas_debiles"] is True


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


def test_verificar_textos_pequenos_respeta_umbral():
    thresholds = get_flexo_thresholds()
    contenido_riesgo = {
        "blocks": [
            {
                "lines": [
                    {
                        "spans": [
                            {
                                "size": thresholds.min_text_pt - 0.1,
                                "font": "Test",
                                "text": "hola",
                                "bbox": [0, 0, 10, 10],
                                "color": 0,
                            }
                        ]
                    }
                ]
            }
        ]
    }
    advertencias, overlay = verificar_textos_pequenos(contenido_riesgo, thresholds)
    assert any("Texto pequeño" in a for a in advertencias)
    assert overlay and overlay[0]["tipo"] == "texto_pequeno"

    contenido_seguro = {
        "blocks": [
            {
                "lines": [
                    {
                        "spans": [
                            {
                                "size": thresholds.min_text_pt,
                                "font": "Test",
                                "text": "hola",
                                "bbox": [0, 0, 10, 10],
                                "color": 0,
                            }
                        ]
                    }
                ]
            }
        ]
    }
    advertencias_seguras, overlay_seguro = verificar_textos_pequenos(
        contenido_seguro, thresholds
    )
    assert any("No se encontraron textos" in a for a in advertencias_seguras)
    assert overlay_seguro == []


def test_pipeline_v2_flag_off_compat_aliases(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = _setup_revision_app(tmp_path, monkeypatch, use_flag=False, tac_v2=None, tac_legacy=None)
    pdf_path = tmp_path / "archivo.pdf"
    _make_pdf(pdf_path)

    client = app.test_client()
    data = {
        "material": "Papel",
        "anilox_lpi": "150",
        "anilox_bcm": "2.5",
        "paso_cilindro": "400",
        "velocidad_impresion": "180",
    }

    with capture_templates(app) as templates:
        with open(pdf_path, "rb") as fh:
            response = client.post(
                "/revision",
                data={**data, "archivo_revision": (fh, "archivo.pdf")},
                content_type="multipart/form-data",
            )

    assert response.status_code == 200
    assert templates, "Se esperaba que se renderice una plantilla"
    template, context = templates[-1]
    assert template.name == "resultado_flexo.html"
    assert context["USE_PIPELINE_V2"] is False

    diagnostico_json = context["diagnostico_json"]
    suma_cmyk = round(
        sum(diagnostico_json["cobertura_por_canal"].values()) if diagnostico_json["cobertura_por_canal"] else 0,
        2,
    )
    assert pytest.approx(diagnostico_json["tac_total_v2"], rel=1e-6) == suma_cmyk
    assert pytest.approx(diagnostico_json["tac_total"], rel=1e-6) == suma_cmyk
    assert pytest.approx(diagnostico_json["cobertura_estimada"], rel=1e-6) == suma_cmyk
    assert pytest.approx(diagnostico_json["cobertura_base_sum"], rel=1e-6) == suma_cmyk
    assert diagnostico_json["lpi"] == 150
    assert pytest.approx(diagnostico_json["bcm"], rel=1e-6) == 2.5
    assert pytest.approx(diagnostico_json["paso"], rel=1e-6) == 400.0
    assert pytest.approx(diagnostico_json["velocidad"], rel=1e-6) == 180.0


def test_pipeline_v2_flag_on_prefiere_v2(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = _setup_revision_app(tmp_path, monkeypatch, use_flag=True, tac_v2=None, tac_legacy=205.7)
    pdf_path = tmp_path / "archivo.pdf"
    _make_pdf(pdf_path)

    client = app.test_client()
    data = {
        "material": "Film",
        "anilox_lpi": "160",
        "anilox_bcm": "3.1",
        "paso_cilindro": "500",
        "velocidad_impresion": "190",
    }

    with capture_templates(app) as templates:
        with open(pdf_path, "rb") as fh:
            response = client.post(
                "/revision",
                data={**data, "archivo_revision": (fh, "archivo.pdf")},
                content_type="multipart/form-data",
            )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "window.USE_PIPELINE_V2 = true" in html
    template, context = templates[-1]
    diagnostico_json = context["diagnostico_json"]
    suma_cmyk = round(
        sum(diagnostico_json["cobertura_por_canal"].values()) if diagnostico_json["cobertura_por_canal"] else 0,
        2,
    )
    assert f"<span id=\"tac-total\">{round(suma_cmyk, 2)}" in html
    assert pytest.approx(diagnostico_json["tac_total_v2"], rel=1e-6) == suma_cmyk
    assert pytest.approx(diagnostico_json["tac_total"], rel=1e-6) == 205.7


def _post_revision(app, pdf_path, data):
    client = app.test_client()
    with capture_templates(app) as templates:
        with open(pdf_path, "rb") as fh:
            response = client.post(
                "/revision",
                data={**data, "archivo_revision": (fh, "archivo.pdf")},
                content_type="multipart/form-data",
            )
    return response, templates


def test_pipeline_json_only_sin_duplicados(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    tinta_por_canal = {"C": 1.24, "M": 1.24, "Y": 1.23, "K": 0.11}
    diag_override = {
        "ancho_util_m": 0.04,
        "coef_material": 0.48,
        "tinta_ml_min": 3.82,
        "tinta_por_canal_ml_min": tinta_por_canal,
    }
    cobertura_override = {"Cian": 81.0, "Magenta": 81.0, "Amarillo": 80.1, "Negro": 7.0}
    app = _setup_revision_app(
        tmp_path,
        monkeypatch,
        use_flag=True,
        tac_v2=249.1,
        tac_legacy=None,
        diag_json_override=diag_override,
        cobertura_override=cobertura_override,
    )
    pdf_path = tmp_path / "archivo.pdf"
    _make_pdf(pdf_path)

    data = {
        "material": "Film",
        "anilox_lpi": "150",
        "anilox_bcm": "1.0",
        "paso_cilindro": "400",
        "velocidad_impresion": "80",
    }
    response, templates = _post_revision(app, pdf_path, data)

    assert response.status_code == 200
    template, context = templates[-1]
    assert template.name == "resultado_flexo.html"
    dj = context["diagnostico_json"]
    assert pytest.approx(dj["tinta_ml_min"], rel=1e-6) == 3.82
    html = response.data.decode("utf-8")
    assert "324.93 ml/min" not in html
    assert '"tinta_ml_min": 3.82' in html


def test_riesgo_relativo_por_ideal(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cobertura_override = {"Cian": 55.0, "Magenta": 48.0, "Amarillo": 42.0, "Negro": 35.0}
    tinta_por_canal = {"C": 30.1, "M": 29.4, "Y": 28.6, "K": 29.1}
    diag_override = {
        "tinta_ml_min": 117.2,
        "tinta_por_canal_ml_min": tinta_por_canal,
        "tinta_ideal_ml_min": 120.0,
        "ink_risk": {
            "level": 0,
            "label": "Verde",
            "reasons": ["Dentro de ±10% del ideal (117.20 vs 120 ml/min)."],
        },
    }
    app = _setup_revision_app(
        tmp_path,
        monkeypatch,
        use_flag=True,
        tac_v2=None,
        tac_legacy=None,
        diag_json_override=diag_override,
        cobertura_override=cobertura_override,
    )
    pdf_path = tmp_path / "archivo.pdf"
    _make_pdf(pdf_path)

    data = {
        "material": "Film",
        "anilox_lpi": "140",
        "anilox_bcm": "2.2",
        "paso_cilindro": "450",
        "velocidad_impresion": "120",
    }
    response, templates = _post_revision(app, pdf_path, data)

    assert response.status_code == 200
    template, context = templates[-1]
    dj = context["diagnostico_json"]
    assert dj["ink_risk"]["level"] == 0
    html = response.get_data(as_text=True)
    assert "Riesgo global Rojo" not in html


def test_simulador_igual_a_backend_en_valores_iniciales(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cobertura_override = {"Cian": 81.0, "Magenta": 81.0, "Amarillo": 80.1, "Negro": 7.0}
    material_coef = coeficiente_material("Film") or coeficiente_material("film") or 0.48
    params = InkParams(
        anilox_lpi=150,
        anilox_bcm=1.0,
        velocidad_m_min=80.0,
        ancho_util_m=0.04,
        coef_material=float(material_coef),
    )
    thresholds = get_flexo_thresholds("film", params.anilox_lpi)
    coverage_letters = {"C": 81.0, "M": 81.0, "Y": 80.1, "K": 7.0}
    esperado = calcular_transmision_tinta(params, coverage_letters, thresholds)
    diag_override = {
        "ancho_util_m": params.ancho_util_m,
        "coef_material": params.coef_material,
        "tinta_ml_min": esperado.ml_min_global,
        "tinta_por_canal_ml_min": esperado.ml_min_por_canal,
    }
    app = _setup_revision_app(
        tmp_path,
        monkeypatch,
        use_flag=True,
        tac_v2=249.1,
        tac_legacy=None,
        diag_json_override=diag_override,
        cobertura_override=cobertura_override,
    )
    pdf_path = tmp_path / "archivo.pdf"
    _make_pdf(pdf_path)

    data = {
        "material": "Film",
        "anilox_lpi": str(params.anilox_lpi),
        "anilox_bcm": str(params.anilox_bcm),
        "paso_cilindro": "400",
        "velocidad_impresion": str(params.velocidad_m_min),
    }
    response, templates = _post_revision(app, pdf_path, data)
    assert response.status_code == 200
    _, context = templates[-1]
    dj = context["diagnostico_json"]
    assert pytest.approx(dj["tinta_ml_min"], rel=1e-6) == pytest.approx(esperado.ml_min_global, rel=1e-6)
    params_ctx = InkParams(
        anilox_lpi=int(dj["anilox_lpi"]),
        anilox_bcm=float(dj["anilox_bcm"]),
        velocidad_m_min=float(dj["velocidad_impresion"]),
        ancho_util_m=float(dj["ancho_util_m"]),
        coef_material=float(dj["coef_material"]),
    )
    resultado = calcular_transmision_tinta(params_ctx, dj["cobertura_por_canal"], thresholds)
    assert pytest.approx(resultado.ml_min_global, rel=1e-6) == pytest.approx(
        dj["tinta_ml_min"], rel=1e-6
    )
    for canal, valor in dj["tinta_por_canal_ml_min"].items():
        assert pytest.approx(resultado.ml_min_por_canal[canal], rel=1e-6) == pytest.approx(
            valor, rel=1e-6
        )


def test_no_recalculo_en_diagnostico_y_reporte(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    diag_override = {
        "ancho_util_m": 0.05,
        "coef_material": 0.5,
        "tinta_ml_min": 4.2,
        "tinta_por_canal_ml_min": {"C": 1.4, "M": 1.4, "Y": 1.3, "K": 0.1},
    }
    app = _setup_revision_app(
        tmp_path,
        monkeypatch,
        use_flag=True,
        tac_v2=250.0,
        tac_legacy=None,
        diag_json_override=diag_override,
    )
    pdf_path = tmp_path / "archivo.pdf"
    _make_pdf(pdf_path)
    data = {
        "material": "Papel",
        "anilox_lpi": "130",
        "anilox_bcm": "1.0",
        "paso_cilindro": "500",
        "velocidad_impresion": "70",
    }
    response, templates = _post_revision(app, pdf_path, data)
    assert response.status_code == 200
    _, context = templates[-1]
    analisis = context["analisis"]
    assert analisis["diagnostico_json"]["tinta_ml_min"] == context["diagnostico_json"]["tinta_ml_min"]
    assert analisis["diagnostico_json"]["cobertura_por_canal"] == context["diagnostico_json"][
        "cobertura_por_canal"
    ]


def test_unidades_ml_min_consistentes(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = _setup_revision_app(
        tmp_path,
        monkeypatch,
        use_flag=True,
        tac_v2=249.1,
        tac_legacy=None,
        diag_json_override={"tinta_ml_min": 5.5, "tinta_por_canal_ml_min": {"C": 1.5, "M": 1.5, "Y": 1.5, "K": 1.0}},
    )
    pdf_path = tmp_path / "archivo.pdf"
    _make_pdf(pdf_path)
    data = {
        "material": "Cartón",
        "anilox_lpi": "140",
        "anilox_bcm": "1.1",
        "paso_cilindro": "450",
        "velocidad_impresion": "75",
    }
    response, _ = _post_revision(app, pdf_path, data)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "ml/s" not in html
def test_simulador_prefiere_json_y_decimales(monkeypatch):
    thresholds = FlexoThresholds(
        min_text_pt=4.0,
        min_stroke_mm=0.2,
        min_resolution_dpi=300,
        tac_warning=279,
        tac_critical=300,
        edge_distance_mm=1.5,
        min_bleed_mm=3.0,
    )

    monkeypatch.setattr(
        "simulador_riesgos.get_flexo_thresholds", lambda material=None, anilox_lpi=None: thresholds
    )

    html_dict = simular_riesgos({"tac_total_v2": 279.5})
    assert "TAC 279% - 300%" in html_dict

    html_texto = simular_riesgos("TAC 279,5%")
    assert "TAC 279% - 300%" in html_texto


def test_verificar_textos_pequenos_limites():
    thresholds = FlexoThresholds(min_text_pt=4.0)
    contenido = {
        "blocks": [
            {
                "lines": [
                    {
                        "spans": [
                            {"size": 3.9, "font": "Test", "text": "A", "bbox": [0, 0, 10, 10]},
                            {"size": 4.0, "font": "Test", "text": "B", "bbox": [0, 10, 10, 20]},
                            {"size": 4.1, "font": "Test", "text": "C", "bbox": [0, 20, 10, 30]},
                        ]
                    }
                ]
            }
        ]
    }
    advertencias, overlay = verificar_textos_pequenos(contenido, thresholds)
    assert any("3.9" in a for a in advertencias)
    assert any(o["bbox"][1] == 0 for o in overlay)
    assert not any("4.0" in a for a in advertencias if "No se encontraron" in a)
    assert all(o["bbox"][1] != 20 for o in overlay)


def test_verificar_lineas_finas_limites():
    class FakePage:
        def __init__(self, drawings):
            self._drawings = drawings

        def get_drawings(self):
            return self._drawings

    thresholds = FlexoThresholds(min_stroke_mm=0.25)
    pt_per_mm = 72 / 25.4
    riesgo_page = FakePage(
        [
            {"width": thresholds.min_stroke_mm * pt_per_mm * 0.96, "bbox": [0, 0, 10, 10]},
            {"width": thresholds.min_stroke_mm * pt_per_mm, "bbox": [10, 0, 20, 10]},
            {"width": thresholds.min_stroke_mm * pt_per_mm * 1.04, "bbox": [20, 0, 30, 10]},
        ]
    )
    advertencias, overlay = verificar_lineas_finas_v2(riesgo_page, "", thresholds)
    assert any("trazos" in a.lower() for a in advertencias)
    assert any(o["bbox"][0] == 0 for o in overlay)
    assert all(o["bbox"][0] != 20 for o in overlay)


def test_simulador_riesgos_tac_limites():
    assert "TAC" not in simular_riesgos("Reporte TAC 279%")
    html_med = simular_riesgos("Reporte TAC 300%")
    assert "TAC 280%" in html_med
    html_alto = simular_riesgos("Reporte TAC 321%")
    assert "TAC >" in html_alto


def test_preview_bbox_scaling_exact(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=144, height=144)
    page.insert_textbox(fitz.Rect(10, 10, 40, 40), "Test")
    pdf_path = tmp_path / "bbox.pdf"
    doc.save(pdf_path)
    doc.close()

    advertencias = [
        {"tipo": "texto_pequeno", "bbox": [10, 10, 30, 30], "descripcion": ""}
    ]

    app = Flask(__name__)
    app.static_folder = str(tmp_path)
    with app.app_context():
        _, _, _, iconos = generar_preview_diagnostico(str(pdf_path), advertencias, dpi=144)

    bbox_px = iconos[0]["bbox"]
    assert abs(bbox_px[0] - 20) <= 1
    assert abs(bbox_px[1] - 20) <= 1
    assert abs(bbox_px[2] - 60) <= 1
    assert abs(bbox_px[3] - 60) <= 1


def test_revisar_sangrado_detecta_borde(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_textbox(fitz.Rect(1, 1, 50, 30), "Edge")
    thresholds = FlexoThresholds(min_bleed_mm=3.0)
    adv, overlay = revisar_sangrado(page, thresholds=thresholds)
    assert any("cercanos al borde" in a for a in adv)
    assert overlay

    page2 = doc.new_page(width=200, height=200)
    page2.insert_textbox(fitz.Rect(50, 50, 120, 120), "Safe")
    adv_ok, overlay_ok = revisar_sangrado(page2, thresholds=thresholds)
    assert any("Margen de seguridad" in a for a in adv_ok)
    assert overlay_ok == []
    doc.close()


def test_config_mock_afecta_todas_las_rutas(monkeypatch):
    custom = FlexoThresholds(min_text_pt=5.0, min_stroke_mm=0.4, min_bleed_mm=4.0)

    monkeypatch.setattr(
        "advertencias_disenio.get_flexo_thresholds",
        lambda material=None: custom,
    )
    monkeypatch.setattr(
        "simulador_riesgos.get_flexo_thresholds",
        lambda material=None, anilox_lpi=None: custom,
    )

    contenido = {
        "blocks": [
            {
                "lines": [
                    {
                        "spans": [
                            {"size": 4.8, "font": "Test", "text": "pequeño", "bbox": [0, 0, 10, 10]}
                        ]
                    }
                ]
            }
        ]
    }
    advertencias, _ = verificar_textos_pequenos(contenido)
    assert any("4.8" in a for a in advertencias)

    html = simular_riesgos("Texto pequeño 4.8 pt")
    assert "Textos < 5" in html


def test_verificar_lineas_finas_respeta_mm():
    class FakePage:
        def __init__(self, drawings):
            self._drawings = drawings

        def get_drawings(self):
            return self._drawings

    thresholds = get_flexo_thresholds(material="papel")
    pt_per_mm = 72 / 25.4
    riesgo_page = FakePage(
        [
            {
                "width": thresholds.min_stroke_mm * pt_per_mm * 0.9,
                "bbox": [0, 0, 10, 10],
            }
        ]
    )
    advertencias, overlay = verificar_lineas_finas_v2(riesgo_page, "papel", thresholds)
    assert any("trazos por debajo" in a.lower() for a in advertencias)
    assert overlay and overlay[0]["tipo"] == "trazo_fino"

    seguro_page = FakePage(
        [
            {
                "width": thresholds.min_stroke_mm * pt_per_mm * 1.2,
                "bbox": [0, 0, 10, 10],
            }
        ]
    )
    advertencias_ok, overlay_ok = verificar_lineas_finas_v2(
        seguro_page, "papel", thresholds
    )
    assert any("Trazos ≥" in a for a in advertencias_ok)
    assert overlay_ok == []


def test_get_flexo_thresholds_profiles():
    default = get_flexo_thresholds()
    film = get_flexo_thresholds("Film")
    assert film.min_stroke_mm < default.min_stroke_mm

    high_lpi = get_flexo_thresholds(anilox_lpi=700)
    assert high_lpi.min_text_pt < default.min_text_pt
