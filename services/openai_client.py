import os
from functools import lru_cache
from typing import Any, Dict, List, Optional


@lru_cache(maxsize=1)
def get_openai_client():
    """Devuelve un cliente OpenAI inicializado de forma diferida."""
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - depende de librería externa
        raise RuntimeError("La librería OpenAI no está disponible") from exc

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurada")
    return OpenAI(api_key=api_key)


def create_chat_completion(
    *,
    messages: List[Dict[str, Any]],
    model: str,
    temperature: Optional[float] = None,
    response_format: Optional[Dict[str, Any]] = None,
):
    """Ejecuta una llamada estándar de chat completions."""
    client = get_openai_client()

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if response_format is not None:
        payload["response_format"] = response_format

    return client.chat.completions.create(**payload)


def create_json_chat_completion(
    *,
    messages: List[Dict[str, Any]],
    model: str,
    temperature: Optional[float] = None,
):
    """Ejecuta una completion solicitando explícitamente salida JSON."""
    return create_chat_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
    )


def transcribe_audio(*, file_obj, model: str = "whisper-1"):
    """Transcribe audio usando el cliente centralizado."""
    client = get_openai_client()
    return client.audio.transcriptions.create(
        model=model,
        file=file_obj,
    )
