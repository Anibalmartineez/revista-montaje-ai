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

