"""Audio transcription service using OpenAI Whisper API."""

import tempfile
from pathlib import Path

import openai

from app.config import settings

client = openai.OpenAI(api_key=settings.openai_api_key)


async def transcribe_voice(audio_data: bytes, file_extension: str = "ogg") -> str:
    """Transcribe voice audio to text using Whisper.

    Telegram sends voice messages as .ogg (opus codec).
    Whisper accepts ogg directly — no conversion needed.
    """
    with tempfile.NamedTemporaryFile(suffix=f".{file_extension}", delete=True) as tmp:
        tmp.write(audio_data)
        tmp.flush()
        with open(tmp.name, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es",  # default to Spanish; Whisper auto-detects if wrong
            )
    return transcription.text
