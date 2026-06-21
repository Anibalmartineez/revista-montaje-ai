"""CLI interno para calcular y persistir presupuestos desde fixtures JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from .backend.calculation_engine import calculate_quote_from_dict
from .backend.catalog_repository import CatalogRepository
from .backend.errors import PresupuestoError
from .backend.repositories import BudgetRepository
from .backend.serializers import quote_result_to_dict
from .backend.storage import JsonStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sistema_presupuesto.cli",
        description="CLI interno del Sistema Presupuesto.",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Directorio base de datos JSON. Por defecto usa sistema_presupuesto/data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    calcular = subparsers.add_parser("calcular", help="Calcula un presupuesto desde un JSON de entrada.")
    calcular.add_argument("quote_request_json", help="Ruta al archivo quote_request JSON.")

    calcular_guardar = subparsers.add_parser(
        "calcular-y-guardar",
        help="Calcula y guarda un presupuesto en data/presupuestos/.",
    )
    calcular_guardar.add_argument("quote_request_json", help="Ruta al archivo quote_request JSON.")

    subparsers.add_parser("listar", help="Lista presupuestos guardados.")

    ver = subparsers.add_parser("ver", help="Muestra un presupuesto guardado por ID.")
    ver.add_argument("presupuesto_id", help="ID del presupuesto guardado.")

    return parser


def run(argv: list[str] | None = None, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    err = stderr or sys.stderr

    try:
        result = _dispatch(args)
    except (PresupuestoError, OSError, json.JSONDecodeError) as exc:
        _print_json(
            {
                "ok": False,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            },
            err,
        )
        return 1

    _print_json(result, out)
    return 0


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    storage = JsonStorage(args.data_dir) if args.data_dir else JsonStorage()
    catalog_repo = CatalogRepository(storage)
    budget_repo = BudgetRepository(storage)

    if args.command == "calcular":
        payload = _read_input_json(args.quote_request_json)
        result = calculate_quote_from_dict(payload, **catalog_repo.load_all_defaults())
        return {
            "ok": True,
            "action": "calcular",
            "result": quote_result_to_dict(result),
        }

    if args.command == "calcular-y-guardar":
        payload = _read_input_json(args.quote_request_json)
        result = calculate_quote_from_dict(payload, **catalog_repo.load_all_defaults())
        record = budget_repo.save_calculated_budget(result, request_payload=payload)
        return {
            "ok": True,
            "action": "calcular-y-guardar",
            "presupuesto_id": record["presupuesto_id"],
            "record": record,
        }

    if args.command == "listar":
        return {
            "ok": True,
            "action": "listar",
            "presupuestos": budget_repo.list_budgets(),
        }

    if args.command == "ver":
        return {
            "ok": True,
            "action": "ver",
            "record": budget_repo.get_budget(args.presupuesto_id),
        }

    raise ValueError(f"Comando no soportado: {args.command}")


def _read_input_json(path: str) -> dict[str, Any]:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Archivo de entrada no encontrado: {path}")
    with input_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError("El JSON de entrada debe ser un objeto.")
    return payload


def _print_json(payload: dict[str, Any], stream: TextIO) -> None:
    json.dump(payload, stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

