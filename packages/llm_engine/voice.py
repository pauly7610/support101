"""
Voice I/O module — Speech-to-Text (Whisper) and Text-to-Speech (TTS).

Provides async wrappers around OpenAI's audio APIs for voice-enabled
customer support. Gracefully degrades when the OpenAI client or API
key is not available.

Environment variables:
    OPENAI_API_KEY: Required for Whisper and TTS
    VOICE_STT_MODEL: Whisper model (default: whisper-1)
    VOICE_TTS_MODEL: TTS model (default: tts-1)
    VOICE_TTS_VOICE: TTS voice (default: nova)
    VOICE_TTS_SPEED: TTS speed 0.25-4.0 (default: 1.0)
    VOICE_MAX_AUDIO_MB: Max upload size in MB (default: 25)
    VOICE_ENABLED: Enable/disable voice features (default: true)
"""

import io
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

VOICE_ENABLED = os.getenv("VOICE_ENABLED", "true").lower() == "true"
STT_MODEL = os.getenv("VOICE_STT_MODEL", "whisper-1")
TTS_MODEL = os.getenv("VOICE_TTS_MODEL", "tts-1")
TTS_VOICE = os.getenv("VOICE_TTS_VOICE", "nova")
TTS_SPEED = float(os.getenv("VOICE_TTS_SPEED", "1.0"))
MAX_AUDIO_MB = float(os.getenv("VOICE_MAX_AUDIO_MB", "25"))

SUPPORTED_AUDIO_FORMATS = {
    "mp3",
    "mp4",
    "mpeg",
    "mpga",
    "m4a",
    "wav",
    "webm",
    "ogg",
    "flac",
}
SUPPORTED_TTS_VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
SUPPORTED_TTS_FORMATS = {"mp3", "opus", "aac", "flac", "wav", "pcm"}


@dataclass
class TranscriptionResult:
    """Result from speech-to-text transcription."""

    text: str
    language: str | None = None
    duration_seconds: float | None = None
    segments: list[dict[str, Any]] | None = None
    processing_time_ms: float = 0.0


@dataclass
class SynthesisResult:
    """Result from text-to-speech synthesis."""

    audio_bytes: bytes
    format: str = "mp3"
    processing_time_ms: float = 0.0


def _get_openai_client():
    """Get the OpenAI client, or None if unavailable."""
    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.debug("OPENAI_API_KEY not set — voice features disabled")
            return None
        return OpenAI(api_key=api_key)
    except ImportError:
        logger.debug("openai package not installed — voice features disabled")
        return None


async def transcribe(
    audio_data: bytes,
    filename: str = "audio.wav",
    language: str | None = None,
    prompt: str | None = None,
) -> TranscriptionResult:
    """
    Transcribe audio to text using OpenAI Whisper.

    Args:
        audio_data: Raw audio bytes.
        filename: Original filename (used for format detection).
        language: Optional ISO-639-1 language code hint.
        prompt: Optional prompt to guide transcription style.

    Returns:
        TranscriptionResult with transcribed text and metadata.

    Raises:
        ValueError: If voice is disabled or audio format is unsupported.
        RuntimeError: If transcription fails.
    """
    if not VOICE_ENABLED:
        raise ValueError("Voice features are disabled (VOICE_ENABLED=false)")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext and ext not in SUPPORTED_AUDIO_FORMATS:
        raise ValueError(
            f"Unsupported audio format: .{ext}. "
            f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_FORMATS))}"
        )

    size_mb = len(audio_data) / (1024 * 1024)
    if size_mb > MAX_AUDIO_MB:
        raise ValueError(f"Audio file too large: {size_mb:.1f}MB (max: {MAX_AUDIO_MB}MB)")

    client = _get_openai_client()
    if not client:
        raise RuntimeError("OpenAI client unavailable — check OPENAI_API_KEY")

    start = time.time()

    try:
        kwargs: dict[str, Any] = {
            "model": STT_MODEL,
            "file": (filename, io.BytesIO(audio_data)),
            "response_format": "verbose_json",
        }
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        response = client.audio.transcriptions.create(**kwargs)

        processing_ms = (time.time() - start) * 1000

        text = response.text if hasattr(response, "text") else str(response)
        lang = getattr(response, "language", None)
        duration = getattr(response, "duration", None)
        segments = None
        if hasattr(response, "segments"):
            segments = [
                {
                    "id": s.id if hasattr(s, "id") else i,
                    "start": s.start if hasattr(s, "start") else 0,
                    "end": s.end if hasattr(s, "end") else 0,
                    "text": s.text if hasattr(s, "text") else str(s),
                }
                for i, s in enumerate(response.segments)
            ]

        logger.info(
            "Transcribed %s (%.1fMB) in %.0fms: %d chars",
            filename,
            size_mb,
            processing_ms,
            len(text),
        )

        return TranscriptionResult(
            text=text,
            language=lang,
            duration_seconds=duration,
            segments=segments,
            processing_time_ms=processing_ms,
        )

    except Exception as e:
        processing_ms = (time.time() - start) * 1000
        logger.error("Transcription failed after %.0fms: %s", processing_ms, e)
        raise RuntimeError(f"Transcription failed: {str(e)[:300]}") from e


async def synthesize(
    text: str,
    voice: str | None = None,
    model: str | None = None,
    speed: float | None = None,
    response_format: str = "mp3",
) -> SynthesisResult:
    """
    Synthesize text to speech using OpenAI TTS.

    Args:
        text: Text to convert to speech (max 4096 chars).
        voice: TTS voice name (default: nova).
        model: TTS model (default: tts-1).
        speed: Playback speed 0.25-4.0 (default: 1.0).
        response_format: Output format (mp3, opus, aac, flac, wav, pcm).

    Returns:
        SynthesisResult with audio bytes and metadata.

    Raises:
        ValueError: If voice is disabled or parameters are invalid.
        RuntimeError: If synthesis fails.
    """
    if not VOICE_ENABLED:
        raise ValueError("Voice features are disabled (VOICE_ENABLED=false)")

    if len(text) > 4096:
        raise ValueError(f"Text too long: {len(text)} chars (max: 4096)")

    if not text.strip():
        raise ValueError("Text cannot be empty")

    voice = voice or TTS_VOICE
    if voice not in SUPPORTED_TTS_VOICES:
        raise ValueError(
            f"Unsupported voice: {voice}. Supported: {', '.join(sorted(SUPPORTED_TTS_VOICES))}"
        )

    if response_format not in SUPPORTED_TTS_FORMATS:
        raise ValueError(
            f"Unsupported format: {response_format}. "
            f"Supported: {', '.join(sorted(SUPPORTED_TTS_FORMATS))}"
        )

    speed = speed or TTS_SPEED
    if not 0.25 <= speed <= 4.0:
        raise ValueError(f"Speed must be 0.25-4.0, got: {speed}")

    client = _get_openai_client()
    if not client:
        raise RuntimeError("OpenAI client unavailable — check OPENAI_API_KEY")

    start = time.time()

    try:
        response = client.audio.speech.create(
            model=model or TTS_MODEL,
            voice=voice,
            input=text,
            speed=speed,
            response_format=response_format,
        )

        audio_bytes = response.content
        processing_ms = (time.time() - start) * 1000

        logger.info(
            "Synthesized %d chars -> %d bytes (%s) in %.0fms",
            len(text),
            len(audio_bytes),
            response_format,
            processing_ms,
        )

        return SynthesisResult(
            audio_bytes=audio_bytes,
            format=response_format,
            processing_time_ms=processing_ms,
        )

    except Exception as e:
        processing_ms = (time.time() - start) * 1000
        logger.error("TTS synthesis failed after %.0fms: %s", processing_ms, e)
        raise RuntimeError(f"TTS synthesis failed: {str(e)[:300]}") from e
