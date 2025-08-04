import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def chat_completion(prompt, model="gpt-4o", temperature=0.3):
    """Genera una respuesta usando el modelo de chat de OpenAI."""
    respuesta = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return respuesta.choices[0].message.content.strip()


def transcribir_audio(file_obj):
    """Transcribe audio utilizando el modelo Whisper."""
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=file_obj,
    )
    return transcript.text
