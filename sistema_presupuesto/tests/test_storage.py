import json

import pytest

from sistema_presupuesto.backend.errors import JsonDecodeStorageError, JsonFileExistsError, JsonFileNotFoundError, StoragePathError
from sistema_presupuesto.backend.storage import JsonStorage


def test_storage_reads_and_writes_json_inside_base_dir(tmp_path):
    storage = JsonStorage(tmp_path)

    storage.write_json("presupuestos/test.json", {"ok": True})
    payload = storage.read_json("presupuestos/test.json")

    assert payload == {"ok": True}


def test_storage_does_not_overwrite_without_control(tmp_path):
    storage = JsonStorage(tmp_path)
    storage.write_json("presupuestos/test.json", {"ok": True})

    with pytest.raises(JsonFileExistsError):
        storage.write_json("presupuestos/test.json", {"ok": False})


def test_storage_missing_json_raises_controlled_error(tmp_path):
    storage = JsonStorage(tmp_path)

    with pytest.raises(JsonFileNotFoundError):
        storage.read_json("catalogo/no_existe.json")


def test_storage_malformed_json_raises_controlled_error(tmp_path):
    bad_file = tmp_path / "catalogo" / "bad.json"
    bad_file.parent.mkdir(parents=True)
    bad_file.write_text("{bad json", encoding="utf-8")
    storage = JsonStorage(tmp_path)

    with pytest.raises(JsonDecodeStorageError):
        storage.read_json("catalogo/bad.json")


def test_storage_rejects_path_traversal(tmp_path):
    storage = JsonStorage(tmp_path)

    with pytest.raises(StoragePathError):
        storage.write_json("../escape.json", {"ok": True})


def test_storage_lists_json_files(tmp_path):
    storage = JsonStorage(tmp_path)
    storage.write_json("presupuestos/a.json", {"id": "a"})
    storage.write_json("presupuestos/b.json", {"id": "b"})
    (tmp_path / "presupuestos" / "ignore.txt").write_text("x", encoding="utf-8")

    names = [path.name for path in storage.list_json("presupuestos")]

    assert names == ["a.json", "b.json"]


def test_storage_rejects_non_object_json(tmp_path):
    path = tmp_path / "catalogo" / "array.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([]), encoding="utf-8")
    storage = JsonStorage(tmp_path)

    with pytest.raises(JsonDecodeStorageError):
        storage.read_json("catalogo/array.json")
