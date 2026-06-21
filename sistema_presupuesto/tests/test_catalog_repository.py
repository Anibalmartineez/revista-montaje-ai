from pathlib import Path

import pytest

from sistema_presupuesto.backend.catalog_repository import CatalogRepository
from sistema_presupuesto.backend.errors import JsonDecodeStorageError, JsonFileNotFoundError, RepositoryError
from sistema_presupuesto.backend.storage import JsonStorage


def test_catalog_repository_loads_existing_defaults():
    repo = CatalogRepository()

    materiales = repo.load_materiales_default()
    maquinas = repo.load_maquinas_default()
    procesos = repo.load_procesos_default()

    assert materiales["schema"] == "sistema_presupuesto.catalogo.materiales"
    assert maquinas["schema"] == "sistema_presupuesto.catalogo.maquinas"
    assert procesos["schema"] == "sistema_presupuesto.catalogo.procesos"
    assert materiales["materiales"]
    assert maquinas["maquinas"]
    assert procesos["procesos"]


def test_catalog_repository_load_all_defaults():
    catalogs = CatalogRepository().load_all_defaults()

    assert set(catalogs) == {"materiales_catalog", "maquinas_catalog", "procesos_catalog"}


def test_catalog_repository_missing_catalog_raises_controlled_error(tmp_path):
    repo = CatalogRepository(JsonStorage(tmp_path))

    with pytest.raises(JsonFileNotFoundError):
        repo.load_materiales_default()


def test_catalog_repository_malformed_catalog_raises_controlled_error(tmp_path):
    path = Path(tmp_path) / "catalogo" / "materiales_default.json"
    path.parent.mkdir(parents=True)
    path.write_text("{bad json", encoding="utf-8")
    repo = CatalogRepository(JsonStorage(tmp_path))

    with pytest.raises(JsonDecodeStorageError):
        repo.load_materiales_default()


def test_catalog_repository_invalid_structure_raises_repository_error(tmp_path):
    path = Path(tmp_path) / "catalogo" / "materiales_default.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"schema": "otro", "materiales": []}', encoding="utf-8")
    repo = CatalogRepository(JsonStorage(tmp_path))

    with pytest.raises(RepositoryError):
        repo.load_materiales_default()

