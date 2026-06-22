"""Repositorio JSON local para clientes del Sistema Presupuesto."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .errors import JsonFileNotFoundError, RepositoryError, StoragePathError
from .storage import JsonStorage

_CLIENT_ID_PATTERN = re.compile(r"^cli_[0-9]{8}_[a-f0-9]{12}$")
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ClientRepository:
    """Crea, lee, actualiza y elimina clientes en `data/clientes/`."""

    EDITABLE_FIELDS = ("nombre", "empresa", "telefono", "email", "ruc", "notas")

    def __init__(self, storage: JsonStorage | None = None):
        self.storage = storage or JsonStorage()

    def list_clients(self) -> list[dict[str, Any]]:
        clients: list[dict[str, Any]] = []
        for path in self.storage.list_json("clientes"):
            payload = self.storage.read_json(path.relative_to(self.storage.base_dir))
            self._validate_client_record(payload)
            clients.append(payload)
        return sorted(clients, key=lambda item: (item["nombre"].casefold(), item["created_at"]))

    def create_client(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RepositoryError("El cliente debe ser un objeto JSON.")
        now = self._now_iso()
        client = self._normalize_client_payload(payload)
        client["cliente_id"] = self.generate_client_id()
        client["created_at"] = now
        client["updated_at"] = now
        self.storage.write_json(self._client_relative_path(client["cliente_id"]), client, overwrite=False)
        return client

    def get_client(self, cliente_id: str) -> dict[str, Any]:
        self._validate_client_id(cliente_id)
        payload = self.storage.read_json(self._client_relative_path(cliente_id))
        self._validate_client_record(payload)
        return payload

    def update_client(self, cliente_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(patch, dict):
            raise RepositoryError("El patch de cliente debe ser un objeto JSON.")
        current = self.get_client(cliente_id)
        editable = {field: current.get(field, "") for field in self.EDITABLE_FIELDS}
        for field in self.EDITABLE_FIELDS:
            if field in patch:
                editable[field] = patch[field]
        updated = self._normalize_client_payload(editable)
        updated["cliente_id"] = current["cliente_id"]
        updated["created_at"] = current["created_at"]
        updated["updated_at"] = self._now_iso()
        self.storage.write_json(self._client_relative_path(cliente_id), updated, overwrite=True)
        return updated

    def delete_client(self, cliente_id: str) -> dict[str, Any]:
        self._validate_client_id(cliente_id)
        path = self.storage.resolve_path(self._client_relative_path(cliente_id))
        if not path.exists():
            raise JsonFileNotFoundError(f"Archivo JSON no encontrado: clientes/{cliente_id}.json")
        path.unlink()
        return {"deleted": True, "cliente_id": cliente_id}

    @staticmethod
    def generate_client_id() -> str:
        return f"cli_{datetime.now(timezone.utc):%Y%m%d}_{uuid4().hex[:12]}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _client_relative_path(cliente_id: str) -> str:
        return f"clientes/{cliente_id}.json"

    @staticmethod
    def _validate_client_id(cliente_id: str) -> None:
        if not isinstance(cliente_id, str) or not _CLIENT_ID_PATTERN.fullmatch(cliente_id):
            raise StoragePathError("cliente_id invalido.")

    def _normalize_client_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = {field: self._optional_text(payload.get(field)) for field in self.EDITABLE_FIELDS}
        if not client["nombre"]:
            raise RepositoryError("nombre es obligatorio.")
        if client["email"] and not _EMAIL_PATTERN.fullmatch(client["email"]):
            raise RepositoryError("email invalido.")
        return client

    def _validate_client_record(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise RepositoryError("Cliente persistido invalido.")
        for field in ("cliente_id", *self.EDITABLE_FIELDS, "created_at", "updated_at"):
            if field not in payload:
                raise RepositoryError(f"Cliente incompleto: falta {field}.")
        self._validate_client_id(payload["cliente_id"])
        self._normalize_client_payload(payload)
        if not isinstance(payload["created_at"], str) or not payload["created_at"]:
            raise RepositoryError("created_at invalido.")
        if not isinstance(payload["updated_at"], str) or not payload["updated_at"]:
            raise RepositoryError("updated_at invalido.")

    @staticmethod
    def _optional_text(value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise RepositoryError("Los campos de cliente deben ser texto.")
        return value.strip()
