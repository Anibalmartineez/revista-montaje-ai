import pytest

from sistema_presupuesto.backend.client_repository import ClientRepository
from sistema_presupuesto.backend.errors import JsonFileNotFoundError, RepositoryError, StoragePathError
from sistema_presupuesto.backend.storage import JsonStorage


def valid_client(**overrides):
    payload = {
        "nombre": "Cliente Test",
        "empresa": "Empresa Test",
        "telefono": "0981000000",
        "email": "cliente@example.com",
        "ruc": "1234567-8",
        "notas": "Cliente de prueba.",
    }
    payload.update(overrides)
    return payload


def test_client_repository_creates_valid_client(tmp_path):
    repo = ClientRepository(JsonStorage(tmp_path))

    client = repo.create_client(valid_client(cliente_id="ignorado", created_at="ignorado"))

    assert client["cliente_id"].startswith("cli_")
    assert client["nombre"] == "Cliente Test"
    assert client["created_at"] != "ignorado"
    assert client["updated_at"] == client["created_at"]


def test_client_repository_rejects_missing_name(tmp_path):
    repo = ClientRepository(JsonStorage(tmp_path))

    with pytest.raises(RepositoryError):
        repo.create_client(valid_client(nombre=""))


def test_client_repository_rejects_invalid_email(tmp_path):
    repo = ClientRepository(JsonStorage(tmp_path))

    with pytest.raises(RepositoryError):
        repo.create_client(valid_client(email="email-invalido"))


def test_client_repository_lists_clients(tmp_path):
    repo = ClientRepository(JsonStorage(tmp_path))
    repo.create_client(valid_client(nombre="Beta"))
    repo.create_client(valid_client(nombre="Alfa"))

    clients = repo.list_clients()

    assert [client["nombre"] for client in clients] == ["Alfa", "Beta"]


def test_client_repository_gets_client_by_id(tmp_path):
    repo = ClientRepository(JsonStorage(tmp_path))
    created = repo.create_client(valid_client())

    loaded = repo.get_client(created["cliente_id"])

    assert loaded == created


def test_client_repository_updates_client(tmp_path):
    repo = ClientRepository(JsonStorage(tmp_path))
    created = repo.create_client(valid_client())

    updated = repo.update_client(created["cliente_id"], {"nombre": "Cliente Actualizado", "email": ""})

    assert updated["cliente_id"] == created["cliente_id"]
    assert updated["nombre"] == "Cliente Actualizado"
    assert updated["email"] == ""
    assert updated["created_at"] == created["created_at"]


def test_client_repository_deletes_client(tmp_path):
    repo = ClientRepository(JsonStorage(tmp_path))
    created = repo.create_client(valid_client())

    result = repo.delete_client(created["cliente_id"])

    assert result == {"deleted": True, "cliente_id": created["cliente_id"]}
    assert repo.list_clients() == []


def test_client_repository_missing_file_is_controlled(tmp_path):
    repo = ClientRepository(JsonStorage(tmp_path))

    with pytest.raises(JsonFileNotFoundError):
        repo.get_client("cli_20260622_abcdef123456")


def test_client_repository_rejects_invalid_client_id(tmp_path):
    repo = ClientRepository(JsonStorage(tmp_path))

    with pytest.raises(StoragePathError):
        repo.get_client("../cliente")
