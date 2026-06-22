"""Numeracion comercial persistente para presupuestos."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from .errors import JsonFileNotFoundError, RepositoryError
from .storage import JsonStorage

NUMBERING_SCHEMA = "sistema_presupuesto.quote_numbering"
NUMBERING_SCHEMA_VERSION = 1
NUMBERING_FILE = "quote_numbering.json"


class QuoteNumbering:
    """Genera numeros comerciales `PRES-YYYY-000001` por anio."""

    def __init__(self, storage: JsonStorage | None = None, today_provider: Callable[[], date] | None = None):
        self.storage = storage or JsonStorage()
        self.today_provider = today_provider or date.today

    def next_number(self) -> str:
        today = self.today_provider()
        year = str(today.year)
        state = self._load_or_initial_state()
        counters = state["counters"]
        next_value = int(counters.get(year, 0)) + 1
        counters[year] = next_value
        self.storage.write_json(NUMBERING_FILE, state, overwrite=True)
        return self._format_number(year, next_value)

    def status(self) -> dict[str, Any]:
        today = self.today_provider()
        year = str(today.year)
        state = self._load_or_initial_state()
        counters = state["counters"]
        return {
            "schema": NUMBERING_SCHEMA,
            "schema_version": NUMBERING_SCHEMA_VERSION,
            "current_year": year,
            "last_number": int(counters.get(year, 0)),
            "next_number_preview": self._format_number(year, int(counters.get(year, 0)) + 1),
            "counters": dict(counters),
        }

    def _load_or_initial_state(self) -> dict[str, Any]:
        try:
            payload = self.storage.read_json(NUMBERING_FILE)
        except JsonFileNotFoundError:
            return self._initial_state()
        self._validate_state(payload)
        return payload

    @staticmethod
    def _initial_state() -> dict[str, Any]:
        return {
            "schema": NUMBERING_SCHEMA,
            "schema_version": NUMBERING_SCHEMA_VERSION,
            "counters": {},
        }

    @staticmethod
    def _validate_state(payload: dict[str, Any]) -> None:
        if payload.get("schema") != NUMBERING_SCHEMA:
            raise RepositoryError("Estado de numeracion con schema invalido.")
        if payload.get("schema_version") != NUMBERING_SCHEMA_VERSION:
            raise RepositoryError("Estado de numeracion con schema_version invalido.")
        counters = payload.get("counters")
        if not isinstance(counters, dict):
            raise RepositoryError("Estado de numeracion sin counters validos.")
        for year, value in counters.items():
            if not isinstance(year, str) or not year.isdigit() or len(year) != 4:
                raise RepositoryError("Anio de numeracion invalido.")
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise RepositoryError("Contador de numeracion invalido.")

    @staticmethod
    def _format_number(year: str, value: int) -> str:
        return f"PRES-{year}-{value:06d}"
