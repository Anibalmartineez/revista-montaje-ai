"""Repositorios de presupuestos calculados."""

from __future__ import annotations

import copy
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
DEFAULT_BUDGET_STATE = "borrador"
ALLOWED_BUDGET_STATES = frozenset({"borrador", "enviado", "aceptado", "rechazado", "vencido"})
LEGACY_BUDGET_STATES = frozenset({"calculado"})


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
            "estado": DEFAULT_BUDGET_STATE,
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

    def list_budgets(self, *, q: str | None = None, estado: str | None = None) -> list[dict[str, Any]]:
        if estado:
            self._validate_state(estado)
        summaries: list[dict[str, Any]] = []
        for path in self.storage.list_json("presupuestos"):
            payload = self.storage.read_json(path.relative_to(self.storage.base_dir))
            self._validate_budget_record(payload)
            result = payload.get("result") or {}
            costs = result.get("costos") or {}
            summary = self._budget_summary(payload, costs)
            if self._matches_filters(summary, q=q, estado=estado):
                summaries.append(summary)
        return sorted(summaries, key=lambda item: item["created_at"], reverse=True)

    def update_budget_state(self, presupuesto_id: str, estado: str) -> dict[str, Any]:
        self._validate_state(estado)
        payload = self.get_budget(presupuesto_id)
        payload["estado"] = estado
        payload["updated_at"] = self._now_iso()
        self.storage.write_json(self._budget_relative_path(presupuesto_id), payload, overwrite=True)
        return payload

    def duplicate_budget(self, presupuesto_id: str, patch: dict[str, Any] | None = None) -> dict[str, Any]:
        patch = patch or {}
        if not isinstance(patch, dict):
            raise RepositoryError("El patch de duplicacion debe ser un objeto JSON.")
        unsupported = set(patch) - {"observaciones"}
        if unsupported:
            raise RepositoryError("Patch no soportado sin recalculo: " + ", ".join(sorted(unsupported)))

        original = self.get_budget(presupuesto_id)
        budget_id = self.generate_budget_id()
        now = self._now_iso()
        record = {
            "schema": BUDGET_RECORD_SCHEMA,
            "schema_version": BUDGET_RECORD_SCHEMA_VERSION,
            "presupuesto_id": budget_id,
            "numero_comercial": self.numbering.next_number(),
            "version": 1,
            "estado": DEFAULT_BUDGET_STATE,
            "duplicado_de": original["presupuesto_id"],
            "created_at": now,
            "updated_at": now,
            "request": copy.deepcopy(original.get("request")),
            "result": copy.deepcopy(original.get("result")),
        }
        if "observaciones" in patch:
            record["observaciones"] = patch["observaciones"]
        elif "observaciones" in original:
            record["observaciones"] = original["observaciones"]

        self.storage.write_json(self._budget_relative_path(budget_id), record, overwrite=False)
        return record

    @classmethod
    def _budget_summary(cls, payload: dict[str, Any], costs: dict[str, Any]) -> dict[str, Any]:
        request_payload = payload.get("request") or {}
        product = request_payload.get("producto") or {}
        summary = {
            "presupuesto_id": payload["presupuesto_id"],
            "version": payload["version"],
            "estado": cls._record_state(payload),
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
            "fecha": payload["created_at"],
            "producto": product.get("titulo") or product.get("tipo"),
            "cantidad": product.get("cantidad"),
            "precio_final": costs.get("precio_final"),
            "precio_unitario": costs.get("precio_unitario"),
            "moneda": costs.get("moneda"),
        }
        if "numero_comercial" in payload:
            summary["numero_comercial"] = payload["numero_comercial"]
        if "observaciones" in payload:
            summary["observaciones"] = payload["observaciones"]
        return summary

    @classmethod
    def _matches_filters(cls, summary: dict[str, Any], *, q: str | None, estado: str | None) -> bool:
        if estado and summary["estado"] != estado:
            return False
        if not q:
            return True
        needle = q.strip().lower()
        if not needle:
            return True
        haystack = " ".join(
            str(summary.get(key) or "")
            for key in ("presupuesto_id", "numero_comercial", "producto", "observaciones")
        ).lower()
        return needle in haystack

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

    @classmethod
    def _validate_budget_record(cls, payload: dict[str, Any]) -> None:
        if payload.get("schema") != BUDGET_RECORD_SCHEMA:
            raise RepositoryError("BudgetRecord con schema invalido.")
        if payload.get("schema_version") != BUDGET_RECORD_SCHEMA_VERSION:
            raise RepositoryError("BudgetRecord con schema_version invalido.")
        for key in ("presupuesto_id", "version", "created_at", "updated_at", "result"):
            if key not in payload:
                raise RepositoryError(f"BudgetRecord incompleto: falta {key}.")
        state = payload.get("estado")
        if state is not None and state not in ALLOWED_BUDGET_STATES and state not in LEGACY_BUDGET_STATES:
            raise RepositoryError("Estado de presupuesto invalido.")

    @staticmethod
    def _validate_state(estado: str) -> None:
        if estado not in ALLOWED_BUDGET_STATES:
            raise RepositoryError("Estado de presupuesto invalido.")

    @staticmethod
    def _record_state(payload: dict[str, Any]) -> str:
        state = payload.get("estado") or DEFAULT_BUDGET_STATE
        if state in LEGACY_BUDGET_STATES:
            return DEFAULT_BUDGET_STATE
        return state
