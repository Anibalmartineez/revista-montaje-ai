from typing import Any, Dict

from ai_agent.schemas import ToolResponse
from ai_agent.tools_repeat import (
    analizar_layout,
    aplicar_reglas_repeat,
    centrar_layout,
    generar_repeat,
    optimizar_repeat,
    validar_repeat,
)


def _normalize_prompt(prompt: str) -> str:
    return (prompt or "").strip().lower()


def handle_agent_request(prompt: str, layout: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_prompt(prompt)
    if not isinstance(layout, dict):
        return ToolResponse(False, None, "layout_json debe ser un objeto JSON.").to_dict()

    if "analizar" in normalized or "diagnosticar" in normalized:
        analysis = analizar_layout(layout)
        return ToolResponse(
            True,
            layout,
            "Analisis del layout generado.",
            {"analysis": analysis, "tool": "analizar_layout"},
        ).to_dict()

    if "validar" in normalized:
        result = validar_repeat(layout)
        return ToolResponse(
            bool(result.get("ok")),
            layout,
            result.get("message") or "Validacion repeat ejecutada.",
            {"validation": result, "tool": "validar_repeat"},
        ).to_dict()

    if "centrar" in normalized:
        centered = centrar_layout(layout)
        return ToolResponse(
            True,
            centered,
            "Layout centrado dentro del area util.",
            {"analysis": analizar_layout(centered), "tool": "centrar_layout"},
        ).to_dict()

    if "optimizar" in normalized or "mejorar" in normalized:
        try:
            optimized = optimizar_repeat(layout)
        except Exception as exc:
            return ToolResponse(
                False,
                layout,
                str(exc),
                {"details": getattr(exc, "details", []), "tool": "optimizar_repeat"},
            ).to_dict()
        return ToolResponse(
            True,
            optimized,
            "Layout optimizado con herramientas Step & Repeat PRO.",
            {"analysis": analizar_layout(optimized), "tool": "optimizar_repeat"},
        ).to_dict()

    if "repeat" in normalized or "repetir" in normalized or "generar" in normalized:
        try:
            generated = generar_repeat(layout, {})
        except Exception as exc:
            return ToolResponse(
                False,
                layout,
                str(exc),
                {"details": getattr(exc, "details", []), "tool": "generar_repeat"},
            ).to_dict()
        return ToolResponse(
            True,
            generated,
            "Step & Repeat generado con el motor existente.",
            {"analysis": analizar_layout(generated), "tool": "generar_repeat"},
        ).to_dict()

    if "regla" in normalized or "reglas" in normalized:
        ruled = aplicar_reglas_repeat(layout, {})
        return ToolResponse(
            True,
            ruled,
            "Reglas repeat aplicadas.",
            {"analysis": analizar_layout(ruled), "tool": "aplicar_reglas_repeat"},
        ).to_dict()

    if "zona" in normalized or "ubicacion" in normalized or "ubicación" in normalized:
        return ToolResponse(
            False,
            layout,
            "Para cambiar zonas por IA usa el asistente OpenAI con una instruccion que indique diseno y ubicacion.",
            {"tool": "set_design_zone", "available_zones": ["auto", "top", "bottom", "left", "right", "center"]},
        ).to_dict()

    return ToolResponse(
        False,
        layout,
        "No se reconocio una accion. Proba con: analizar, centrar, optimizar o generar repeat.",
        {"tool": None},
    ).to_dict()
