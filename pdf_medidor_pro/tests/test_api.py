import io

import fitz

from app import app as main_app
from pdf_medidor_pro.services.geometry import mm_to_pt


def pdf_bytes(width_mm: float = 100, height_mm: float = 50) -> bytes:
    doc = fitz.open()
    doc.new_page(width=mm_to_pt(width_mm), height=mm_to_pt(height_mm))
    stream = doc.tobytes()
    doc.close()
    return stream


def test_main_app_serves_pdf_medidor_pro_ui_and_static():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        ui_response = client.get("/pdf-medidor-pro")
        css_response = client.get("/pdf-medidor-pro/static/css/pdf_medidor_pro.css")
        js_response = client.get("/pdf-medidor-pro/static/js/pdf_medidor_pro.js")

    assert ui_response.status_code == 200
    assert "PDF Medidor Pro" in ui_response.get_data(as_text=True)
    assert css_response.status_code == 200
    assert ".pmp-shell" in css_response.get_data(as_text=True)
    assert js_response.status_code == 200
    assert "/api/pdf-medidor-pro" in js_response.get_data(as_text=True)


def test_pdf_medidor_pro_health_endpoint():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        response = client.get("/api/pdf-medidor-pro/health")

    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_upload_rejects_non_pdf():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        response = client.post(
            "/api/pdf-medidor-pro/upload",
            data={"pdf": (io.BytesIO(b"not a pdf"), "sample.txt")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_EXTENSION"


def test_upload_accepts_pdf_and_returns_preview():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        response = client.post(
            "/api/pdf-medidor-pro/upload",
            data={"pdf": (io.BytesIO(pdf_bytes()), "sample.pdf")},
            content_type="multipart/form-data",
        )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["medidas_auto"]["mediabox_mm"]["ancho"] == 100
    assert payload["preview_url"].startswith("/pdf-medidor-pro/previews/")


def test_export_normalizes_json_contract():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        response = client.post(
            "/api/pdf-medidor-pro/export",
            json={
                "archivo": "sample.pdf",
                "pagina": 1,
                "medidas_auto": {"mediabox_mm": {"ancho": 100, "alto": 50}},
                "medidas_manual": {"ancho_final_mm": 90, "alto_final_mm": 40},
                "calibracion": {"activa": True, "factor_escala": 1.1},
                "origen_medida_final": "manual",
                "confianza": "alta",
            },
        )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["export"]["archivo"] == "sample.pdf"
    assert payload["url"].startswith("/api/pdf-medidor-pro/exports/")


def test_existing_main_routes_still_respond():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        index_response = client.get("/")
        presupuesto_response = client.get("/sistema-presupuesto")

    assert index_response.status_code == 200
    assert presupuesto_response.status_code == 200
