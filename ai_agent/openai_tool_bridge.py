import json
import os
from typing import Any, Callable, Dict, List, Optional

from ai_agent.tools_repeat import (
    analizar_layout,
    aplicar_reglas_repeat,
    centrar_layout,
    generar_repeat,
    optimizar_repeat,
)


# Cambiar el modelo aca si se quiere probar otro perfil/costo.
OPENAI_STEP_REPEAT_MODEL = os.environ.get("OPENAI_STEP_REPEAT_MODEL", "gpt-5.4-mini")

# Ajustar estas instrucciones para cambiar el comportamiento global del asistente.
SYSTEM_PROMPT = """
Sos un asistente de preprensa offset enfocado en Step & Repeat PRO.
Debes usar tools locales para analizar, centrar, optimizar o regenerar layouts.
No inventes layouts manualmente.
Si necesitas modificar el montaje, llama a la tool adecuada.
Prioriza acciones simples y seguras.
Si la intencion no esta clara, responde breve sin tool call.
No apliques cambios directamente al sistema; solo devolve resultados para revision del usuario.
""".strip()


def _layout_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "description": "Layout completo del Editor Visual IA. El backend usara siempre el layout recibido por HTTP.",
        "additionalProperties": True,
    }


def _open_object_schema(description: str) -> Dict[str, Any]:
    return {
        "type": "object",
        "description": description,
        "additionalProperties": True,
    }


# Agregar nuevas tools aca. La ejecucion real se controla con TOOL_DISPATCH.
OPENAI_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "name": "analizar_layout",
        "description": "Analiza slots, area usada, area libre, aprovechamiento y espacios muertos aproximados.",
        "parameters": {
            "type": "object",
            "properties": {"layout": _layout_schema()},
            "required": ["layout"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "centrar_layout",
        "description": "Centra el bloque de slots desbloqueados de la cara activa dentro del area util.",
        "parameters": {
            "type": "object",
            "properties": {"layout": _layout_schema()},
            "required": ["layout"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "optimizar_repeat",
        "description": "Genera una propuesta Step & Repeat PRO optimizada y centrada usando las tools locales.",
        "parameters": {
            "type": "object",
            "properties": {"layout": _layout_schema()},
            "required": ["layout"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "generar_repeat",
        "description": "Regenera Step & Repeat PRO usando el motor repeat existente.",
        "parameters": {
            "type": "object",
            "properties": {
                "layout": _layout_schema(),
                "config": _open_object_schema("Overrides opcionales para generar repeat."),
            },
            "required": ["layout"],
            "additionalProperties": False,
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "aplicar_reglas_repeat",
        "description": "Aplica reglas simples de Step & Repeat PRO sobre el layout.",
        "parameters": {
            "type": "object",
            "properties": {
                "layout": _layout_schema(),
                "reglas": _open_object_schema("Reglas opcionales: prioridad_por_diseno, zona_sugerida, etc."),
            },
            "required": ["layout", "reglas"],
            "additionalProperties": False,
        },
        "strict": False,
    },
]


def _response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return str(text).strip()
    fragments: List[str] = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                fragments.append(str(value))
    return "\n".join(fragments).strip()


def _output_item_to_input(item: Any) -> Any:
    if hasattr(item, "model_dump"):
        return item.model_dump(exclude_none=True)
    if hasattr(item, "dict"):
        return item.dict()
    return item


def _tool_calls(response: Any) -> List[Any]:
    return [
        item
        for item in (getattr(response, "output", []) or [])
        if getattr(item, "type", None) == "function_call"
    ]


def _parse_tool_args(tool_call: Any) -> Dict[str, Any]:
    raw_args = getattr(tool_call, "arguments", None) or "{}"
    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError:
        return {}
    return args if isinstance(args, dict) else {}


def _analysis_for_layout(layout: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(layout, dict):
        return None
    try:
        return analizar_layout(layout)
    except Exception:
        return None


def _execute_analizar(layout: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    analysis = analizar_layout(layout)
    return {
        "success": True,
        "layout": None,
        "message": "Analisis del layout generado.",
        "data": {"analysis": analysis},
    }


def _execute_centrar(layout: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    next_layout = centrar_layout(layout)
    return {
        "success": True,
        "layout": next_layout,
        "message": "Layout centrado dentro del area util.",
        "data": {"analysis": _analysis_for_layout(next_layout)},
    }


def _execute_optimizar(layout: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    next_layout = optimizar_repeat(layout)
    return {
        "success": True,
        "layout": next_layout,
        "message": "Layout optimizado con Step & Repeat PRO.",
        "data": {"analysis": _analysis_for_layout(next_layout)},
    }


def _execute_generar(layout: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    config = args.get("config") if isinstance(args.get("config"), dict) else {}
    next_layout = generar_repeat(layout, config)
    return {
        "success": True,
        "layout": next_layout,
        "message": "Step & Repeat generado con el motor existente.",
        "data": {"analysis": _analysis_for_layout(next_layout)},
    }


def _execute_reglas(layout: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    reglas = args.get("reglas") if isinstance(args.get("reglas"), dict) else {}
    next_layout = aplicar_reglas_repeat(layout, reglas)
    return {
        "success": True,
        "layout": next_layout,
        "message": "Reglas repeat aplicadas.",
        "data": {"analysis": _analysis_for_layout(next_layout)},
    }


TOOL_DISPATCH: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {
    "analizar_layout": _execute_analizar,
    "centrar_layout": _execute_centrar,
    "optimizar_repeat": _execute_optimizar,
    "generar_repeat": _execute_generar,
    "aplicar_reglas_repeat": _execute_reglas,
}


def _safe_tool_output(result: Dict[str, Any]) -> Dict[str, Any]:
    layout = result.get("layout")
    analysis = result.get("data", {}).get("analysis") if isinstance(result.get("data"), dict) else None
    return {
        "success": bool(result.get("success")),
        "message": result.get("message") or "",
        "has_layout": isinstance(layout, dict),
        "analysis": analysis,
    }


def _call_local_tool(name: str, args: Dict[str, Any], request_layout: Dict[str, Any]) -> Dict[str, Any]:
    if name not in TOOL_DISPATCH:
        raise ValueError(f"Tool no permitida: {name}")
    if not isinstance(request_layout, dict):
        raise ValueError("layout_json debe ser un objeto JSON.")
    return TOOL_DISPATCH[name](request_layout, args)


def run_openai_step_repeat_assistant(prompt: str, layout: Dict[str, Any], client: Optional[Any] = None) -> Dict[str, Any]:
    if client is None and not os.environ.get("OPENAI_API_KEY"):
        return {
            "ok": False,
            "error": "OPENAI_API_KEY no esta configurada.",
        }
    if not isinstance(layout, dict):
        return {
            "ok": False,
            "error": "layout_json debe ser un objeto JSON.",
        }

    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    user_payload = {
        "prompt": prompt,
        "layout": layout,
        "nota_seguridad": "Decidi una tool, pero no inventes layouts. El backend ejecutara tools locales.",
    }
    input_items: List[Any] = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": json.dumps(user_payload, ensure_ascii=False),
                }
            ],
        }
    ]

    response = client.responses.create(
        model=OPENAI_STEP_REPEAT_MODEL,
        instructions=SYSTEM_PROMPT,
        input=input_items,
        tools=OPENAI_TOOLS,
        parallel_tool_calls=False,
    )

    calls = _tool_calls(response)
    if not calls:
        return {
            "ok": True,
            "message": _response_text(response) or "No se ejecuto ninguna tool.",
            "layout": None,
            "tool_used": None,
            "raw_tool_result": None,
        }

    conversation: List[Any] = input_items + [_output_item_to_input(item) for item in getattr(response, "output", [])]
    last_result: Optional[Dict[str, Any]] = None
    tool_used: Optional[str] = None

    for call in calls:
        tool_used = getattr(call, "name", None)
        args = _parse_tool_args(call)
        try:
            last_result = _call_local_tool(tool_used, args, layout)
            output = _safe_tool_output(last_result)
        except Exception as exc:
            output = {
                "success": False,
                "message": f"Fallo al ejecutar tool local: {str(exc)}",
            }
            last_result = {
                "success": False,
                "layout": None,
                "message": output["message"],
                "data": None,
            }

        conversation.append(
            {
                "type": "function_call_output",
                "call_id": getattr(call, "call_id", ""),
                "output": json.dumps(output, ensure_ascii=False),
            }
        )

    final_response = client.responses.create(
        model=OPENAI_STEP_REPEAT_MODEL,
        instructions=SYSTEM_PROMPT,
        input=conversation,
        tools=OPENAI_TOOLS,
        parallel_tool_calls=False,
    )

    message = _response_text(final_response)
    if not message and last_result:
        message = last_result.get("message") or "Accion IA ejecutada."

    layout_result = last_result.get("layout") if last_result else None
    raw_tool_result = _safe_tool_output(last_result or {})
    return {
        "ok": bool(last_result and last_result.get("success")),
        "message": message,
        "layout": layout_result if isinstance(layout_result, dict) else None,
        "tool_used": tool_used,
        "raw_tool_result": raw_tool_result,
        "data": last_result.get("data") if last_result else None,
    }
