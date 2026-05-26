from __future__ import annotations

import argparse
import asyncio
import os
import sys

from ai_agent.editor_advisor.agent import run_editor_advisor
from ai_agent.editor_advisor.schemas import EditorAdvisorReport


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
    parser.add_argument(
        "--codex-prompt-only",
        action="store_true",
        help="Imprime solo prompt_para_codex, listo para copiar en Codex.",
    )
    return parser


def _format_report_output(
    report: EditorAdvisorReport, *, pretty: bool = False, codex_prompt_only: bool = False
) -> str:
    if codex_prompt_only:
        prompt = report.prompt_para_codex.strip()
        if not prompt:
            raise ValueError("El reporte no incluyo prompt_para_codex.")
        return prompt

    indent = 2 if pretty else None
    return report.model_dump_json(indent=indent)


async def _main_async() -> int:
    args = _parser().parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY no esta configurada.", file=sys.stderr)
        return 2
    report = await run_editor_advisor(" ".join(args.prompt), model=args.model)
    try:
        print(
            _format_report_output(
                report,
                pretty=args.pretty,
                codex_prompt_only=args.codex_prompt_only,
            )
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    return 0


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
