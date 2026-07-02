import io

import fitz

from app import app as main_app
from pdf_medidor_pro.services.geometry import mm_to_pt


def pdf_bytes(width_mm: float = 100, height_mm: float = 50, pages: list[tuple[float, float]] | None = None) -> bytes:
    doc = fitz.open()
    sizes = pages or [(width_mm, height_mm)]
    for page_width, page_height in sizes:
        doc.new_page(width=mm_to_pt(page_width), height=mm_to_pt(page_height))
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


def test_render_page_endpoint_renders_selected_pdf_page():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        upload = client.post(
            "/api/pdf-medidor-pro/upload",
            data={"pdf": (io.BytesIO(pdf_bytes(pages=[(100, 50), (80, 40)])), "multi.pdf")},
            content_type="multipart/form-data",
        )
        stored_filename = upload.get_json()["stored_filename"]
        response = client.post(
            "/api/pdf-medidor-pro/render-page",
            json={"stored_filename": stored_filename, "pagina": 2},
        )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["pagina"] == 2
    assert payload["page_count"] == 2
    assert payload["medidas_auto"]["mediabox_mm"]["ancho"] == 80
    assert payload["preview_url"].startswith("/pdf-medidor-pro/previews/")


def test_render_page_endpoint_rejects_invalid_page():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        upload = client.post(
            "/api/pdf-medidor-pro/upload",
            data={"pdf": (io.BytesIO(pdf_bytes()), "one.pdf")},
            content_type="multipart/form-data",
        )
        stored_filename = upload.get_json()["stored_filename"]
        response = client.post(
            "/api/pdf-medidor-pro/render-page",
            json={"stored_filename": stored_filename, "pagina": 5},
        )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "PAGE_RENDER_FAILED"


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
                "mediciones": [
                    {
                        "id": "rect_1",
                        "tipo": "rectangulo",
                        "origen": "manual",
                        "nombre": "Rectangulo manual",
                        "color": "#2563eb",
                        "stroke_width": 2,
                        "pagina": 1,
                        "ancho_mm": 20,
                        "alto_mm": 10,
                        "x_mm": 5,
                        "y_mm": 5,
                        "area_mm2": 200,
                        "perimetro_mm": 60,
                        "angulo_deg": 0,
                        "confianza": 0.9,
                    }
                ],
                "page_count": 2,
                "paginas": [
                    {
                        "pagina": 1,
                        "medidas_auto": {"mediabox_mm": {"ancho": 100, "alto": 50}},
                        "medidas_manual": {"ancho_final_mm": 90, "alto_final_mm": 40},
                        "origen_medida_final": "manual",
                        "confianza": "alta",
                        "mediciones": [],
                    },
                    {
                        "pagina": 2,
                        "medidas_auto": {"mediabox_mm": {"ancho": 80, "alto": 40}},
                        "medidas_manual": {},
                        "origen_medida_final": "auto",
                        "confianza": "media",
                        "mediciones": [],
                    },
                ],
            },
        )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["export"]["archivo"] == "sample.pdf"
    assert payload["export"]["mediciones"][0]["origen"] == "manual"
    assert payload["export"]["mediciones"][0]["color"] == "#2563eb"
    assert payload["export"]["mediciones"][0]["stroke_width"] == 2
    assert payload["export"]["mediciones"][0]["pagina"] == 1
    assert payload["export"]["page_count"] == 2
    assert payload["export"]["paginas"][1]["pagina"] == 2
    assert payload["export"]["paginas"][1]["medidas_auto"]["mediabox_mm"]["ancho"] == 80
    assert payload["url"].startswith("/api/pdf-medidor-pro/exports/")


def test_existing_main_routes_still_respond():
    main_app.config["TESTING"] = True

    with main_app.test_client() as client:
        index_response = client.get("/")
        presupuesto_response = client.get("/sistema-presupuesto")

    assert index_response.status_code == 200
    assert presupuesto_response.status_code == 200
