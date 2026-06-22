"""Repositorios de presupuestos calculados."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .defaults import BUDGET_RECORD_SCHEMA, BUDGET_RECORD_SCHEMA_VERSION
from .errors import RepositoryError, StoragePathError
from .models import QuoteResult
from .quote_numbering import QuoteNumbering
from .serializers import quote_result_to_dict
from .storage import JsonStorage

_BUDGET_ID_PATTERN = re.compile(r"^psp_[0-9]{8}_[a-f0-9]{12}$")


class BudgetRepository:
    """Guarda, lee y lista presupuestos en `data/presupuestos/`."""

    def __init__(self, storage: JsonStorage | None = None, numbering: QuoteNumbering | None = None):
        self.storage = storage or JsonStorage()
        self.numbering = numbering or QuoteNumbering(self.storage)

    def save_calculated_budget(
        self,
        result: QuoteResult | dict[str, Any],
        *,
        request_payload: dict[str, Any] | None = None,
        presupuesto_id: str | None = None,
    ) -> dict[str, Any]:
        budget_id = presupuesto_id or self.generate_budget_id()
        self._validate_budget_id(budget_id)
        now = self._now_iso()
        result_payload = quote_result_to_dict(result) if isinstance(result, QuoteResult) else result
        record = {
            "schema": BUDGET_RECORD_SCHEMA,
            "schema_version": BUDGET_RECORD_SCHEMA_VERSION,
            "presupuesto_id": budget_id,
            "numero_comercial": self.numbering.next_number(),
            "version": 1,
            "estado": "calculado",
            "created_at": now,
            "updated_at": now,
            "request": request_payload,
            "result": result_payload,
        }
        self.storage.write_json(self._budget_relative_path(budget_id), record, overwrite=False)
        return record

    def get_budget(self, presupuesto_id: str) -> dict[str, Any]:
        self._validate_budget_id(presupuesto_id)
        payload = self.storage.read_json(self._budget_relative_path(presupuesto_id))
        self._validate_budget_record(payload)
        return payload

    def list_budgets(self) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for path in self.storage.list_json("presupuestos"):
            payload = self.storage.read_json(path.relative_to(self.storage.base_dir))
            self._validate_budget_record(payload)
            result = payload.get("result") or {}
            costs = result.get("costos") or {}
            summaries.append(
                self._budget_summary(payload, costs)
            )
        return sorted(summaries, key=lambda item: item["created_at"])

    @staticmethod
    def _budget_summary(payload: dict[str, Any], costs: dict[str, Any]) -> dict[str, Any]:
        summary = {
            "presupuesto_id": payload["presupuesto_id"],
            "version": payload["version"],
            "estado": payload["estado"],
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
            "precio_final": costs.get("precio_final"),
            "moneda": costs.get("moneda"),
        }
        if "numero_comercial" in payload:
            summary["numero_comercial"] = payload["numero_comercial"]
        return summary

    @staticmethod
    def generate_budget_id() -> str:
        return f"psp_{datetime.now(timezone.utc):%Y%m%d}_{uuid4().hex[:12]}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _budget_relative_path(presupuesto_id: str) -> str:
        return f"presupuestos/{presupuesto_id}.json"

    @staticmethod
    def _validate_budget_id(presupuesto_id: str) -> None:
        if not _BUDGET_ID_PATTERN.fullmatch(presupuesto_id):
            raise StoragePathError("presupuesto_id invalido.")

    @staticmethod
    def _validate_budget_record(payload: dict[str, Any]) -> None:
        if payload.get("schema") != BUDGET_RECORD_SCHEMA:
            raise RepositoryError("BudgetRecord con schema invalido.")
        if payload.get("schema_version") != BUDGET_RECORD_SCHEMA_VERSION:
            raise RepositoryError("BudgetRecord con schema_version invalido.")
        for key in ("presupuesto_id", "version", "estado", "created_at", "updated_at", "result"):
            if key not in payload:
                raise RepositoryError(f"BudgetRecord incompleto: falta {key}.")
