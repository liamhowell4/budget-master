"""Whisper transcription client for audio-to-text."""
import io
import logging

import openai

from backend.endpoints import Endpoints

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_bytes: bytes, filename: str = "recording.wav") -> str:
    """Transcribe audio using OpenAI Whisper API (async).

    Args:
        audio_bytes: Raw audio file bytes (WAV, MP3, etc.)
        filename: Filename with extension for format detection

    Returns:
        Transcribed text string, or empty string if audio is empty/invalid
    """
    if not audio_bytes:
        return ""

    try:
        endpoints = Endpoints()
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename  # OpenAI requires filename with extension

        response = await endpoints.openai_async_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return response.text
    except (openai.APIError, openai.APITimeoutError) as e:
        logger.error("Whisper API error: %s", e)
        return ""
    except Exception as e:
        logger.error("Unexpected error during audio transcription: %s", e)
        return ""
