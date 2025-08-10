import io
from pathlib import Path
import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import fitz
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from montaje_offset_personalizado import montar_pliego_offset_personalizado


def _crear_pdf_buffer(ancho_mm, alto_mm):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(ancho_mm * mm, alto_mm * mm))
    c.drawString(10, 10, "test")
    c.save()
    buf.seek(0)
    return buf


def test_montaje_pro_valido(tmp_path):
    pdf_buf = _crear_pdf_buffer(50, 50)
    specs = [{
        "file": pdf_buf,
        "filename": "test.pdf",
        "reps": 4,
        "rotate": False,
        "bleed_mm": 0,
        "cutmarks": False,
        "align": "left",
    }]
    pro_config = {
        "pliego_w_mm": 200,
        "pliego_h_mm": 200,
        "margen_izq_mm": 10,
        "margen_der_mm": 10,
        "margen_sup_mm": 10,
        "margen_inf_mm": 10,
        "sep_h_mm": 5,
        "sep_v_mm": 5,
        "export_area_util": False,
        "preview": False,
    }
    output_path, resumen = montar_pliego_offset_personalizado(specs, pro_config)
    assert Path(output_path).exists()
    doc = fitz.open(output_path)
    assert len(doc) == 1
    doc.close()
    assert resumen[0]["reps_montadas"] == 4


def test_montaje_pro_error_si_no_caben(tmp_path):
    pdf_buf = _crear_pdf_buffer(50, 50)
    specs = [{
        "file": pdf_buf,
        "filename": "test.pdf",
        "reps": 20,
        "rotate": False,
        "bleed_mm": 0,
        "cutmarks": False,
        "align": "left",
    }]
    pro_config = {
        "pliego_w_mm": 100,
        "pliego_h_mm": 100,
        "margen_izq_mm": 10,
        "margen_der_mm": 10,
        "margen_sup_mm": 10,
        "margen_inf_mm": 10,
        "sep_h_mm": 5,
        "sep_v_mm": 5,
        "export_area_util": False,
        "preview": False,
    }
    with pytest.raises(ValueError):
        montar_pliego_offset_personalizado(specs, pro_config)
