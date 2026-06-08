from __future__ import annotations

import os
from pathlib import Path

from agents import Agent, Runner, function_tool

from ai_agent.editor_advisor.schemas import EditorAdvisorReport
from ai_agent.editor_advisor import tools as advisor_tools


DEFAULT_MODEL = os.environ.get("OPENAI_EDITOR_ADVISOR_MODEL", "gpt-5.5")
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "editor_advisor.md"


def _load_instructions() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@function_tool
def read_repo_file(path: str, max_chars: int = 12000) -> str:
    """Lee un archivo allowlisted del repositorio sin modificarlo."""
    return advisor_tools.read_repo_file(path, max_chars=max_chars)


@function_tool
def search_repo(pattern: str, max_matches: int = 80) -> str:
    """Busca texto en areas seguras del repositorio."""
    return advisor_tools.search_repo(pattern, max_matches=max_matches)


@function_tool
def list_editor_files() -> list[str]:
    """Lista archivos canonicos disponibles para analizar el Editor Visual IA."""
    return advisor_tools.list_editor_files()


@function_tool
def summarize_editor_architecture() -> str:
    """Devuelve un resumen deterministico de la arquitectura actual del editor."""
    return advisor_tools.summarize_editor_architecture()


@function_tool
def summarize_editor_ux_surface() -> str:
    """Resume senales UX/DOM read-only del panel derecho y frontend del editor."""
    return advisor_tools.summarize_editor_ux_surface()


@function_tool
def summarize_editor_modular_surface() -> str:
    """Resume el mapa post 6C-1: modulos JS, entrypoint y riesgos pendientes."""
    return advisor_tools.summarize_editor_modular_surface()


@function_tool
def list_validation_commands() -> list[str]:
    """Lista comandos de validacion recomendados para cambios futuros."""
    return advisor_tools.list_validation_commands()


def build_editor_advisor_agent(model: str | None = None) -> Agent:
    return Agent(
        name="Editor Visual IA Offset Advisor",
        model=model or DEFAULT_MODEL,
        instructions=_load_instructions(),
        tools=[
            read_repo_file,
            search_repo,
            list_editor_files,
            summarize_editor_architecture,
            summarize_editor_ux_surface,
            summarize_editor_modular_surface,
            list_validation_commands,
        ],
        output_type=EditorAdvisorReport,
    )


async def run_editor_advisor(prompt: str, model: str | None = None) -> EditorAdvisorReport:
    agent = build_editor_advisor_agent(model=model)
    result = await Runner.run(agent, prompt)
    return result.final_output
