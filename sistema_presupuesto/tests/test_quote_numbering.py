import json
from datetime import date

import pytest

from sistema_presupuesto.backend.errors import JsonDecodeStorageError
from sistema_presupuesto.backend.quote_numbering import QuoteNumbering
from sistema_presupuesto.backend.storage import JsonStorage


class Today:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


def test_quote_numbering_generates_first_number_of_year(tmp_path):
    numbering = QuoteNumbering(JsonStorage(tmp_path), today_provider=lambda: date(2026, 6, 22))

    assert numbering.next_number() == "PRES-2026-000001"


def test_quote_numbering_generates_consecutive_numbers(tmp_path):
    numbering = QuoteNumbering(JsonStorage(tmp_path), today_provider=lambda: date(2026, 6, 22))

    assert numbering.next_number() == "PRES-2026-000001"
    assert numbering.next_number() == "PRES-2026-000002"


def test_quote_numbering_restarts_in_new_year(tmp_path):
    today = Today(date(2026, 12, 31))
    numbering = QuoteNumbering(JsonStorage(tmp_path), today_provider=today)

    assert numbering.next_number() == "PRES-2026-000001"
    today.value = date(2027, 1, 1)
    assert numbering.next_number() == "PRES-2027-000001"


def test_quote_numbering_persists_state(tmp_path):
    storage = JsonStorage(tmp_path)
    first = QuoteNumbering(storage, today_provider=lambda: date(2026, 6, 22))
    second = QuoteNumbering(storage, today_provider=lambda: date(2026, 6, 22))

    assert first.next_number() == "PRES-2026-000001"
    assert second.next_number() == "PRES-2026-000002"
    state = json.loads((tmp_path / "quote_numbering.json").read_text(encoding="utf-8"))
    assert state["counters"]["2026"] == 2


def test_quote_numbering_handles_missing_json_as_initial_state(tmp_path):
    numbering = QuoteNumbering(JsonStorage(tmp_path), today_provider=lambda: date(2026, 6, 22))

    assert numbering.status()["last_number"] == 0
    assert numbering.status()["next_number_preview"] == "PRES-2026-000001"


def test_quote_numbering_invalid_json_raises_controlled_error(tmp_path):
    (tmp_path / "quote_numbering.json").write_text("{bad json", encoding="utf-8")
    numbering = QuoteNumbering(JsonStorage(tmp_path), today_provider=lambda: date(2026, 6, 22))

    with pytest.raises(JsonDecodeStorageError):
        numbering.next_number()
