from pathlib import Path

import pytest

from sistema_presupuesto.backend.catalog_repository import CatalogRepository
from sistema_presupuesto.backend.errors import JsonDecodeStorageError, JsonFileNotFoundError, RepositoryError
from sistema_presupuesto.backend.storage import JsonStorage

ROOT = Path(__file__).resolve().parents[1]


def copy_catalogs(tmp_path):
    catalog_dir = tmp_path / "catalogo"
    catalog_dir.mkdir(parents=True)
    for source in (ROOT / "data" / "catalogo").glob("*.json"):
        (catalog_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def valid_material(**overrides):
    item = {
        "id": "material_custom_test",
        "nombre": "Material custom test",
        "tipo": "papel_test",
        "gramaje_g_m2": "1",
        "formato_pliego_mm": {"ancho": "1", "alto": "1"},
        "costo": {
            "modo": "por_pliego",
            "moneda": "PYG",
            "valor": "0",
            "unidad": "pliego",
            "es_valor_ejemplo": True,
        },
        "merma_recomendada_pct": "0",
        "activo": True,
    }
    item.update(overrides)
    return item


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


def test_catalog_repository_combines_default_and_custom(tmp_path):
    copy_catalogs(tmp_path)
    repo = CatalogRepository(JsonStorage(tmp_path))

    created = repo.create_custom("materiales", valid_material())
    combined = repo.list_combined("materiales")

    assert created["id"] == "material_custom_test"
    assert any(item["id"] == "couche_150" for item in combined["materiales"])
    custom = next(item for item in combined["materiales"] if item["id"] == "material_custom_test")
    assert custom["origen_catalogo"] == "custom"


def test_catalog_repository_custom_overrides_default_by_id(tmp_path):
    copy_catalogs(tmp_path)
    repo = CatalogRepository(JsonStorage(tmp_path))

    repo.create_custom(
        "materiales",
        valid_material(id="couche_150", nombre="Papel custom override"),
    )
    combined = repo.list_combined("materiales")
    matches = [item for item in combined["materiales"] if item["id"] == "couche_150"]

    assert len(matches) == 1
    assert matches[0]["nombre"] == "Papel custom override"
    assert matches[0]["origen_catalogo"] == "custom"


def test_catalog_repository_rejects_invalid_custom(tmp_path):
    copy_catalogs(tmp_path)
    repo = CatalogRepository(JsonStorage(tmp_path))

    with pytest.raises(RepositoryError):
        repo.create_custom("materiales", {"id": "material_invalido"})


def test_catalog_repository_updates_custom(tmp_path):
    copy_catalogs(tmp_path)
    repo = CatalogRepository(JsonStorage(tmp_path))
    repo.create_custom("materiales", valid_material())

    updated = repo.update_custom("materiales", "material_custom_test", {"nombre": "Material actualizado"})

    assert updated["nombre"] == "Material actualizado"
    custom = repo.list_custom("materiales")
    assert custom["materiales"][0]["nombre"] == "Material actualizado"


def test_catalog_repository_deletes_custom(tmp_path):
    copy_catalogs(tmp_path)
    repo = CatalogRepository(JsonStorage(tmp_path))
    repo.create_custom("materiales", valid_material())

    result = repo.delete_custom("materiales", "material_custom_test")

    assert result == {"deleted": True, "id": "material_custom_test"}
    assert repo.list_custom("materiales")["materiales"] == []
