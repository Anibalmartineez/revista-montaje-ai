from services.openai_client import create_chat_completion, transcribe_audio as _transcribe_audio


def chat_completion(prompt, model="gpt-4o", temperature=0.3):
    """Genera una respuesta usando el modelo de chat de OpenAI."""
    respuesta = create_chat_completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return respuesta.choices[0].message.content.strip()


def transcribir_audio(file_obj):
    """Transcribe audio utilizando el modelo Whisper."""
    transcript = _transcribe_audio(file_obj=file_obj, model="whisper-1")
    return transcript.text
