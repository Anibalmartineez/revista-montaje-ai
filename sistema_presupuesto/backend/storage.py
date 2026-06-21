"""Persistencia JSON local para Sistema Presupuesto.

Esta capa solo lee/escribe JSON dentro de `sistema_presupuesto/data/`.
No conoce Flask, UI ni Editor Offset Visual.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from .errors import JsonDecodeStorageError, JsonFileExistsError, JsonFileNotFoundError, StoragePathError

MODULE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = MODULE_ROOT / "data"


class JsonStorage:
    """Adaptador seguro para leer y escribir JSON bajo un directorio base."""

    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir or DEFAULT_DATA_DIR).resolve()

    def read_json(self, relative_path: str | Path) -> dict[str, Any]:
        path = self.resolve_path(relative_path)
        if not path.exists():
            raise JsonFileNotFoundError(f"Archivo JSON no encontrado: {relative_path}")
        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except json.JSONDecodeError as exc:
            raise JsonDecodeStorageError(f"JSON mal formado: {relative_path}") from exc
        if not isinstance(payload, dict):
            raise JsonDecodeStorageError(f"El JSON debe contener un objeto: {relative_path}")
        return payload

    def write_json(self, relative_path: str | Path, payload: dict[str, Any], *, overwrite: bool = False) -> Path:
        if not isinstance(payload, dict):
            raise JsonDecodeStorageError("Solo se pueden persistir objetos JSON.")
        path = self.resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise JsonFileExistsError(f"El archivo ya existe: {relative_path}")

        temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            with temp_path.open("w", encoding="utf-8", newline="\n") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            temp_path.replace(path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        return path

    def list_json(self, relative_dir: str | Path) -> list[Path]:
        directory = self.resolve_path(relative_dir)
        if not directory.exists():
            return []
        if not directory.is_dir():
            raise StoragePathError(f"No es directorio: {relative_dir}")
        return sorted(path for path in directory.glob("*.json") if path.is_file())

    def resolve_path(self, relative_path: str | Path) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise StoragePathError("No se permiten rutas absolutas.")
        resolved = (self.base_dir / candidate).resolve(strict=False)
        try:
            common = os.path.commonpath([str(self.base_dir), str(resolved)])
        except ValueError as exc:
            raise StoragePathError("Ruta fuera del directorio base.") from exc
        if common != str(self.base_dir):
            raise StoragePathError("Ruta fuera del directorio base.")
        return resolved

