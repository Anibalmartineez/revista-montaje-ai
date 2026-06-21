import json
from pathlib import Path

import pytest

from sistema_presupuesto.backend.calculation_engine import calculate_quote_from_dict
from sistema_presupuesto.backend.catalog_repository import CatalogRepository
from sistema_presupuesto.backend.errors import JsonFileExistsError, JsonFileNotFoundError, StoragePathError
from sistema_presupuesto.backend.repositories import BudgetRepository
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
    repo = BudgetRepository(JsonStorage(tmp_path))
    budget_id = "psp_20260621_abcdef123456"

    record = repo.save_calculated_budget(result, request_payload=request_payload, presupuesto_id=budget_id)
    loaded = repo.get_budget(budget_id)

    assert record["presupuesto_id"] == budget_id
    assert loaded["result"]["costos"]["precio_final"] == record["result"]["costos"]["precio_final"]
    assert loaded["schema"] == "sistema_presupuesto.budget_record"
    assert (tmp_path / "presupuestos" / f"{budget_id}.json").exists()


def test_budget_repository_lists_budgets(tmp_path):
    request_payload, result = calculated_result()
    repo = BudgetRepository(JsonStorage(tmp_path))

    repo.save_calculated_budget(result, request_payload=request_payload, presupuesto_id="psp_20260621_aaaaaaaaaaaa")
    repo.save_calculated_budget(result, request_payload=request_payload, presupuesto_id="psp_20260621_bbbbbbbbbbbb")
    summaries = repo.list_budgets()

    assert [item["presupuesto_id"] for item in summaries] == [
        "psp_20260621_aaaaaaaaaaaa",
        "psp_20260621_bbbbbbbbbbbb",
    ]
    assert all(item["precio_final"] for item in summaries)


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

