"""Errores de dominio para contratos del Sistema Presupuesto."""

from __future__ import annotations


class PresupuestoError(Exception):
    """Error base del modulo de presupuestos."""


class ContractValidationError(PresupuestoError):
    """Error bloqueante de validacion de contrato."""

    def __init__(self, message: str, report=None):
        super().__init__(message)
        self.report = report


class CatalogValidationError(ContractValidationError):
    """Error bloqueante relacionado con referencias de catalogo."""


class SerializationError(PresupuestoError):
    """Error al convertir datos entre JSON y modelos internos."""


class StorageError(PresupuestoError):
    """Error base de persistencia JSON local."""


class StoragePathError(StorageError):
    """Ruta invalida o intento de salir del directorio permitido."""


class JsonFileNotFoundError(StorageError):
    """Archivo JSON esperado no existe."""


class JsonDecodeStorageError(StorageError):
    """Archivo JSON mal formado."""


class JsonFileExistsError(StorageError):
    """Se intento sobrescribir un archivo existente sin autorizacion."""


class RepositoryError(PresupuestoError):
    """Error base de repositorios."""
