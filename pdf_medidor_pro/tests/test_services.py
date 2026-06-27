from pathlib import Path

import fitz

from pdf_medidor_pro.services.calibration_engine import calculate_scale_factor
from pdf_medidor_pro.services.export_json import build_export_payload
from pdf_medidor_pro.services.geometry import mm_to_pt
from pdf_medidor_pro.services.pdf_analyzer import analyze_pdf_boxes
from pdf_medidor_pro.services.pdf_renderer import render_first_page


def make_pdf(path: Path, width_mm: float = 100, height_mm: float = 50) -> Path:
    doc = fitz.open()
    doc.new_page(width=mm_to_pt(width_mm), height=mm_to_pt(height_mm))
    doc.save(path)
    doc.close()
    return path


def test_analyze_pdf_boxes_returns_dimensions_in_mm(tmp_path):
    pdf_path = make_pdf(tmp_path / "sample.pdf", 100, 50)

    result = analyze_pdf_boxes(pdf_path)

    assert result["pagina"] == 1
    assert result["page_count"] == 1
    assert result["medidas_auto"]["mediabox_mm"]["ancho"] == 100
    assert result["medidas_auto"]["mediabox_mm"]["alto"] == 50


def test_render_first_page_creates_png(tmp_path):
    pdf_path = make_pdf(tmp_path / "sample.pdf", 80, 40)
    output_path = tmp_path / "preview.png"

    result = render_first_page(pdf_path, output_path, dpi=72)

    assert output_path.exists()
    assert result["filename"] == "preview.png"
    assert result["width_px"] > 0
    assert result["height_px"] > 0


def test_calculate_scale_factor():
    assert calculate_scale_factor(50, 100) == 2


def test_build_export_payload_normalizes_contract():
    payload = build_export_payload(
        archivo="trabajo.pdf",
        pagina=1,
        medidas_auto={"mediabox_mm": {"ancho": "100", "alto": "50"}},
        medidas_manual={"ancho_final_mm": "90.1234", "alto_final_mm": "40"},
        calibracion={"activa": True, "factor_escala": "1.25"},
        origen_medida_final="manual",
        confianza="alta",
    )

    assert payload["archivo"] == "trabajo.pdf"
    assert payload["medidas_auto"]["mediabox_mm"] == {"ancho": 100.0, "alto": 50.0}
    assert payload["medidas_auto"]["cropbox_mm"] == {"ancho": 0.0, "alto": 0.0}
    assert payload["medidas_manual"]["ancho_final_mm"] == 90.123
    assert payload["calibracion"] == {"activa": True, "factor_escala": 1.25}
