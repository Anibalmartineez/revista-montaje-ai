"""Defaults explicitos para el motor de Fase 4.

Los valores monetarios son ficticios y sirven solo para fixtures/tests.
"""

from __future__ import annotations

from decimal import Decimal

QUOTE_RESULT_SCHEMA = "sistema_presupuesto.quote_result"
QUOTE_RESULT_SCHEMA_VERSION = 1
BUDGET_RECORD_SCHEMA = "sistema_presupuesto.budget_record"
BUDGET_RECORD_SCHEMA_VERSION = 1

MONEY_ZERO = Decimal("0")
PERCENT_BASE = Decimal("100")
MM2_PER_M2 = Decimal("1000000")

CTP_COST_PER_PLATE_EXAMPLE = Decimal("45000")
CTP_COST_CURRENCY = "PYG"
