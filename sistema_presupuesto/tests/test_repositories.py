from datetime import date
import json
from pathlib import Path

import pytest

from sistema_presupuesto.backend.calculation_engine import calculate_quote_from_dict
from sistema_presupuesto.backend.catalog_repository import CatalogRepository
from sistema_presupuesto.backend.errors import JsonFileExistsError, JsonFileNotFoundError, RepositoryError, StoragePathError
from sistema_presupuesto.backend.quote_numbering import QuoteNumbering
from sistema_presupuesto.backend.repositories import BudgetRepository
from sistema_presupuesto.backend.serializers import quote_result_to_dict
from sistema_presupuesto.backend.storage import JsonStorage

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def calculated_result():
    catalogs = CatalogRepository().load_all_defaults()
    payload = load_json("data/fixtures/quote_request_volante.json")
    return payload, calculate_quote_from_dict(payload, **catalogs)


def test_budget_repository_saves_and_reads_calculated_budget(tmp_path):
    request_payload, result = calculated_result()
    storage = JsonStorage(tmp_path)
    numbering = QuoteNumbering(storage, today_provider=lambda: date(2026, 6, 22))
    repo = BudgetRepository(storage, numbering=numbering)
    budget_id = "psp_20260621_abcdef123456"

    record = repo.save_calculated_budget(result, request_payload=request_payload, presupuesto_id=budget_id)
    loaded = repo.get_budget(budget_id)

    assert record["presupuesto_id"] == budget_id
    assert record["numero_comercial"] == "PRES-2026-000001"
    assert record["estado"] == "borrador"
    assert loaded["numero_comercial"] == "PRES-2026-000001"
    assert loaded["result"]["costos"]["precio_final"] == record["result"]["costos"]["precio_final"]
    assert loaded["schema"] == "sistema_presupuesto.budget_record"
    assert (tmp_path / "presupuestos" / f"{budget_id}.json").exists()


def test_budget_repository_lists_budgets(tmp_path):
    request_payload, result = calculated_result()
    storage = JsonStorage(tmp_path)
    numbering = QuoteNumbering(storage, today_provider=lambda: date(2026, 6, 22))
    repo = BudgetRepository(storage, numbering=numbering)

    repo.save_calculated_budget(result, request_payload=request_payload, presupuesto_id="psp_20260621_aaaaaaaaaaaa")
    repo.save_calculated_budget(result, request_payload=request_payload, presupuesto_id="psp_20260621_bbbbbbbbbbbb")
    summaries = repo.list_budgets()

    assert {item["presupuesto_id"] for item in summaries} == {
        "psp_20260621_aaaaaaaaaaaa",
        "psp_20260621_bbbbbbbbbbbb",
    }
    assert {item["numero_comercial"] for item in summaries} == {
        "PRES-2026-000002",
        "PRES-2026-000001",
    }
    assert all(item["precio_final"] for item in summaries)
    assert all(item["precio_unitario"] for item in summaries)
    assert all(item["estado"] == "borrador" for item in summaries)


def test_budget_repository_keeps_legacy_budget_without_commercial_number(tmp_path):
    request_payload, result = calculated_result()
    repo = BudgetRepository(JsonStorage(tmp_path))
    budget_id = "psp_20260621_abcdefabcdef"
    record = {
        "schema": "sistema_presupuesto.budget_record",
        "schema_version": 1,
        "presupuesto_id": budget_id,
        "version": 1,
        "estado": "calculado",
        "created_at": "2026-06-21T00:00:00Z",
        "updated_at": "2026-06-21T00:00:00Z",
        "request": request_payload,
        "result": quote_result_to_dict(result),
    }
    legacy_path = tmp_path / "presupuestos" / f"{budget_id}.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(json.dumps(record), encoding="utf-8")

    loaded = repo.get_budget(budget_id)
    summaries = repo.list_budgets()

    assert "numero_comercial" not in loaded
    legacy_summary = next(item for item in summaries if item["presupuesto_id"] == budget_id)
    assert "numero_comercial" not in legacy_summary
    assert legacy_summary["estado"] == "borrador"


def test_budget_repository_uses_borrador_for_missing_legacy_state(tmp_path):
    request_payload, result = calculated_result()
    repo = BudgetRepository(JsonStorage(tmp_path))
    budget_id = "psp_20260621_aaaaabcdef12"
    record = {
        "schema": "sistema_presupuesto.budget_record",
        "schema_version": 1,
        "presupuesto_id": budget_id,
        "version": 1,
        "created_at": "2026-06-21T00:00:00Z",
        "updated_at": "2026-06-21T00:00:00Z",
        "request": request_payload,
        "result": quote_result_to_dict(result),
    }
    legacy_path = tmp_path / "presupuestos" / f"{budget_id}.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(json.dumps(record), encoding="utf-8")

    summary = repo.list_budgets()[0]

    assert summary["estado"] == "borrador"


def test_budget_repository_filters_by_query_and_state(tmp_path):
    request_payload, result = calculated_result()
    storage = JsonStorage(tmp_path)
    numbering = QuoteNumbering(storage, today_provider=lambda: date(2026, 6, 22))
    repo = BudgetRepository(storage, numbering=numbering)

    first_payload = json.loads(json.dumps(request_payload))
    first_payload["producto"]["titulo"] = "Volante primavera"
    second_payload = json.loads(json.dumps(request_payload))
    second_payload["producto"]["titulo"] = "Tarjeta premium"

    first = repo.save_calculated_budget(result, request_payload=first_payload, presupuesto_id="psp_20260621_111111aaaaaa")
    repo.save_calculated_budget(result, request_payload=second_payload, presupuesto_id="psp_20260621_222222bbbbbb")
    repo.update_budget_state(first["presupuesto_id"], "enviado")

    assert [item["presupuesto_id"] for item in repo.list_budgets(q="primavera")] == [first["presupuesto_id"]]
    assert [item["presupuesto_id"] for item in repo.list_budgets(q=first["numero_comercial"])] == [first["presupuesto_id"]]
    assert [item["estado"] for item in repo.list_budgets(estado="enviado")] == ["enviado"]


def test_budget_repository_lists_newest_first(tmp_path):
    repo = BudgetRepository(JsonStorage(tmp_path))
    request_payload, result = calculated_result()
    result_payload = quote_result_to_dict(result)
    for budget_id, created_at in (
        ("psp_20260621_aaaaaaaaaaaa", "2026-06-21T10:00:00Z"),
        ("psp_20260621_bbbbbbbbbbbb", "2026-06-22T10:00:00Z"),
    ):
        record = {
            "schema": "sistema_presupuesto.budget_record",
            "schema_version": 1,
            "presupuesto_id": budget_id,
            "numero_comercial": f"PRES-2026-{1 if budget_id.endswith('aaaa') else 2:06d}",
            "version": 1,
            "estado": "borrador",
            "created_at": created_at,
            "updated_at": created_at,
            "request": request_payload,
            "result": result_payload,
        }
        repo.storage.write_json(f"presupuestos/{budget_id}.json", record, overwrite=False)

    assert [item["presupuesto_id"] for item in repo.list_budgets()] == [
        "psp_20260621_bbbbbbbbbbbb",
        "psp_20260621_aaaaaaaaaaaa",
    ]


def test_budget_repository_updates_state_without_overwriting_payload(tmp_path):
    request_payload, result = calculated_result()
    repo = BudgetRepository(JsonStorage(tmp_path))
    record = repo.save_calculated_budget(
        result,
        request_payload=request_payload,
        presupuesto_id="psp_20260621_abcdef123456",
    )

    updated = repo.update_budget_state(record["presupuesto_id"], "aceptado")

    assert updated["estado"] == "aceptado"
    assert updated["request"] == record["request"]
    assert updated["result"] == record["result"]


def test_budget_repository_rejects_invalid_state(tmp_path):
    request_payload, result = calculated_result()
    repo = BudgetRepository(JsonStorage(tmp_path))
    record = repo.save_calculated_budget(
        result,
        request_payload=request_payload,
        presupuesto_id="psp_20260621_abcdef123456",
    )

    with pytest.raises(RepositoryError):
        repo.update_budget_state(record["presupuesto_id"], "anulado")


def test_budget_repository_duplicates_budget_with_new_identity_and_number(tmp_path):
    request_payload, result = calculated_result()
    storage = JsonStorage(tmp_path)
    numbering = QuoteNumbering(storage, today_provider=lambda: date(2026, 6, 22))
    repo = BudgetRepository(storage, numbering=numbering)
    original = repo.save_calculated_budget(
        result,
        request_payload=request_payload,
        presupuesto_id="psp_20260621_abcdef123456",
    )
    original["archivo_documento"] = "no-copiar.html"
    repo.storage.write_json(repo._budget_relative_path(original["presupuesto_id"]), original, overwrite=True)

    duplicated = repo.duplicate_budget(original["presupuesto_id"], {"observaciones": "Nueva version"})

    assert duplicated["presupuesto_id"] != original["presupuesto_id"]
    assert duplicated["numero_comercial"] == "PRES-2026-000002"
    assert duplicated["numero_comercial"] != original["numero_comercial"]
    assert duplicated["duplicado_de"] == original["presupuesto_id"]
    assert duplicated["estado"] == "borrador"
    assert duplicated["observaciones"] == "Nueva version"
    assert duplicated["request"] == original["request"]
    assert duplicated["result"] == original["result"]
    assert "archivo_documento" not in duplicated


def test_budget_repository_duplicates_legacy_budget_without_commercial_number(tmp_path):
    request_payload, result = calculated_result()
    storage = JsonStorage(tmp_path)
    numbering = QuoteNumbering(storage, today_provider=lambda: date(2026, 6, 22))
    repo = BudgetRepository(storage, numbering=numbering)
    budget_id = "psp_20260621_abcdefabcdef"
    record = {
        "schema": "sistema_presupuesto.budget_record",
        "schema_version": 1,
        "presupuesto_id": budget_id,
        "version": 1,
        "created_at": "2026-06-21T00:00:00Z",
        "updated_at": "2026-06-21T00:00:00Z",
        "request": request_payload,
        "result": quote_result_to_dict(result),
    }
    repo.storage.write_json(f"presupuestos/{budget_id}.json", record, overwrite=False)

    duplicated = repo.duplicate_budget(budget_id)

    assert duplicated["duplicado_de"] == budget_id
    assert duplicated["numero_comercial"] == "PRES-2026-000001"
    assert duplicated["estado"] == "borrador"


def test_budget_repository_does_not_overwrite_existing_budget(tmp_path):
    request_payload, result = calculated_result()
    repo = BudgetRepository(JsonStorage(tmp_path))
    budget_id = "psp_20260621_abcdef123456"
    repo.save_calculated_budget(result, request_payload=request_payload, presupuesto_id=budget_id)

    with pytest.raises(JsonFileExistsError):
        repo.save_calculated_budget(result, request_payload=request_payload, presupuesto_id=budget_id)


def test_budget_repository_missing_budget_raises_controlled_error(tmp_path):
    repo = BudgetRepository(JsonStorage(tmp_path))

    with pytest.raises(JsonFileNotFoundError):
        repo.get_budget("psp_20260621_abcdef123456")


def test_budget_repository_rejects_path_traversal_like_id(tmp_path):
    request_payload, result = calculated_result()
    repo = BudgetRepository(JsonStorage(tmp_path))

    with pytest.raises(StoragePathError):
        repo.save_calculated_budget(result, request_payload=request_payload, presupuesto_id="../escape")


def test_budget_repository_generates_valid_unique_ids():
    first = BudgetRepository.generate_budget_id()
    second = BudgetRepository.generate_budget_id()

    assert first.startswith("psp_")
    assert second.startswith("psp_")
    assert first != second
