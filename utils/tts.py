"""
Text-to-Speech using gTTS (Google Text-to-Speech).

gTTS supports all six languages needed for Indian accessibility users:
English, Hindi, Tamil, Telugu, Kannada, and Bengali — covering ~95% of
India's visually impaired population without any paid API.
"""

import base64
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Maps language selector values to gTTS language codes
GTTS_LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "kn": "kn",
    "bn": "bn",
}


def text_to_speech_base64(text: str, language_code: str = "en") -> dict:
    """
    Convert text to MP3 audio and return as base64-encoded string.

    Returns:
        dict with keys: audio_base64 (str), error (str|None)
    """
    if not text or not text.strip():
        return {"audio_base64": "", "error": "No text provided for speech synthesis."}

    lang = GTTS_LANG_MAP.get(language_code, "en")

    try:
        from gtts import gTTS  # lazy import — keeps startup fast if gtts unused

        tts = gTTS(text=text.strip(), lang=lang, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        audio_base64 = base64.b64encode(audio_buffer.read()).decode("utf-8")

        return {"audio_base64": audio_base64, "error": None}

    except ImportError:
        return {
            "audio_base64": "",
            "error": "gTTS is not installed. Run: pip install gtts",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("TTS error for lang=%s: %s", lang, exc)
        return {
            "audio_base64": "",
            "error": f"Text-to-speech failed: {str(exc)}",
        }


def get_supported_languages() -> list[dict]:
    """Return list of supported languages for the frontend selector."""
    return [
        {"code": "en", "name": "English"},
        {"code": "hi", "name": "Hindi"},
        {"code": "ta", "name": "Tamil"},
        {"code": "te", "name": "Telugu"},
        {"code": "kn", "name": "Kannada"},
        {"code": "bn", "name": "Bengali"},
    ]
