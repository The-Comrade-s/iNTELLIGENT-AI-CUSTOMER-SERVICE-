"""
utils/voice_service.py

Wraps SpeechRecognition (STT) and pyttsx3 (TTS) behind a feature-flag
so the rest of the app can call these functions unconditionally. If
the optional packages or system audio libraries aren't installed in
the runtime environment, the functions return a clear "unavailable"
result instead of crashing -- the chat UI then just hides the voice
controls.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger("ics.voice")

try:
    import speech_recognition as sr  # type: ignore

    _SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:  # pragma: no cover - environment-dependent
    _SPEECH_RECOGNITION_AVAILABLE = False

try:
    import pyttsx3  # type: ignore

    _PYTTSX3_AVAILABLE = True
except ImportError:  # pragma: no cover - environment-dependent
    _PYTTSX3_AVAILABLE = False


@dataclass
class TranscriptionResult:
    success: bool
    text: str = ""
    error: str = ""


def voice_features_available() -> dict[str, bool]:
    """Report which voice capabilities are usable in this environment."""

    return {
        "speech_to_text": _SPEECH_RECOGNITION_AVAILABLE,
        "text_to_speech": _PYTTSX3_AVAILABLE,
    }


def transcribe_audio_bytes(audio_bytes: bytes, language: str = "en-US") -> TranscriptionResult:
    """Transcribe a WAV audio clip to text. Requires SpeechRecognition
    (and its Google Web Speech backend, or another recognizer)."""

    if not _SPEECH_RECOGNITION_AVAILABLE:
        return TranscriptionResult(False, error="Speech-to-text is not installed in this environment (pip install SpeechRecognition).")

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language=language)
        return TranscriptionResult(True, text=text)
    except sr.UnknownValueError:
        return TranscriptionResult(False, error="Could not understand the audio.")
    except sr.RequestError as exc:
        return TranscriptionResult(False, error=f"Speech recognition service error: {exc}")
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected transcription failure")
        return TranscriptionResult(False, error=f"Unexpected error: {exc}")


def synthesize_speech_to_file(text: str, output_path: str) -> bool:
    """Render ``text`` to a .wav/.mp3 file on disk using an offline
    TTS engine. Returns False (without raising) if unavailable."""

    if not _PYTTSX3_AVAILABLE:
        return False
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        return True
    except Exception:  # pragma: no cover - defensive
        logger.exception("TTS synthesis failed")
        return False
