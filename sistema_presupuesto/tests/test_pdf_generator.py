import json
from datetime import date

from sistema_presupuesto.backend.calculation_engine import calculate_quote_from_dict
from sistema_presupuesto.backend.catalog_repository import CatalogRepository
from sistema_presupuesto.backend.pdf_generator import CommercialDocumentGenerator
from sistema_presupuesto.backend.quote_numbering import QuoteNumbering
from sistema_presupuesto.backend.repositories import BudgetRepository
from sistema_presupuesto.backend.serializers import quote_result_to_dict
from sistema_presupuesto.backend.storage import JsonStorage

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def copy_catalogs(tmp_path):
    catalog_dir = tmp_path / "catalogo"
    catalog_dir.mkdir(parents=True)
    for source in (ROOT / "data" / "catalogo").glob("*.json"):
        (catalog_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def saved_record(tmp_path):
    copy_catalogs(tmp_path)
    storage = JsonStorage(tmp_path)
    catalogs = CatalogRepository(storage).load_all_combined()
    payload = load_json("data/fixtures/quote_request_volante.json")
    result = calculate_quote_from_dict(payload, **catalogs)
    numbering = QuoteNumbering(storage, today_provider=lambda: date(2026, 6, 22))
    repo = BudgetRepository(storage, numbering=numbering)
    return repo.save_calculated_budget(result, request_payload=payload, presupuesto_id="psp_20260622_abcdef123456")


def legacy_record(tmp_path):
    copy_catalogs(tmp_path)
    storage = JsonStorage(tmp_path)
    catalogs = CatalogRepository(storage).load_all_combined()
    payload = load_json("data/fixtures/quote_request_volante.json")
    result = calculate_quote_from_dict(payload, **catalogs)
    return {
        "schema": "sistema_presupuesto.budget_record",
        "schema_version": 1,
        "presupuesto_id": "psp_20260622_abcdefabcdef",
        "version": 1,
        "estado": "calculado",
        "created_at": "2026-06-22T00:00:00Z",
        "updated_at": "2026-06-22T00:00:00Z",
        "request": payload,
        "result": quote_result_to_dict(result),
    }


def test_pdf_generator_generates_pdf_from_saved_budget(tmp_path):
    record = saved_record(tmp_path)
    generator = CommercialDocumentGenerator(JsonStorage(tmp_path), use_pdf=True)

    document = generator.generate(record)
    output = tmp_path / document.ruta_relativa

    assert document.tipo_documento == "pdf"
    assert document.numero_comercial == "PRES-2026-000001"
    assert output.exists()
    assert output.parent == tmp_path / "pdfs"
    assert output.read_bytes().startswith(b"%PDF")


def test_pdf_generator_supports_legacy_budget_without_commercial_number(tmp_path):
    record = legacy_record(tmp_path)
    generator = CommercialDocumentGenerator(JsonStorage(tmp_path), use_pdf=False)

    document = generator.generate(record)
    output = tmp_path / document.ruta_relativa

    assert document.tipo_documento == "html"
    assert "numero_comercial" not in document.to_dict()
    assert document.archivo.startswith(record["presupuesto_id"])
    assert record["presupuesto_id"] in output.read_text(encoding="utf-8")


def test_pdf_generator_sanitizes_filename():
    assert CommercialDocumentGenerator.sanitize_filename("../PRES 2026/000001") == "PRES_2026_000001"
