from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from ai_agent.editor_advisor.agent import run_editor_advisor


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Agente asesor CLI-only/read-only para UX/UI SAFE del Editor Visual IA Offset."
    )
    parser.add_argument("prompt", nargs="+", help="Consulta o tarea de analisis para el agente.")
    parser.add_argument(
        "--model",
        default=None,
        help="Modelo a usar. Por defecto OPENAI_EDITOR_ADVISOR_MODEL o gpt-5.5.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Imprime JSON indentado.",
    )
    return parser


async def _main_async() -> int:
    args = _parser().parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY no esta configurada.", file=sys.stderr)
        return 2
    report = await run_editor_advisor(" ".join(args.prompt), model=args.model)
    indent = 2 if args.pretty else None
    print(report.model_dump_json(indent=indent))
    return 0


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
