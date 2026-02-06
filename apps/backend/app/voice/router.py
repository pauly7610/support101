"""
FastAPI router for Voice I/O endpoints.

Endpoints:
- POST /v1/voice/transcribe  — Speech-to-text (Whisper)
- POST /v1/voice/synthesize  — Text-to-speech (TTS)
- POST /v1/voice/chat        — Voice-in → RAG → Voice-out pipeline
"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi_limiter.depends import RateLimiter

from apps.backend.app.auth.jwt import get_current_user
from packages.llm_engine.voice import (
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_TTS_VOICES,
    VOICE_ENABLED,
    synthesize,
    transcribe,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/voice", tags=["Voice I/O"])


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: str | None = Form(None, description="ISO-639-1 language hint"),
    prompt: str | None = Form(None, description="Transcription style prompt"),
    _user=Depends(get_current_user),
    _limiter: None = Depends(RateLimiter(times=10, seconds=60)),
):
    """
    Transcribe an audio file to text using OpenAI Whisper.

    Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac.
    Max file size: 25MB.
    """
    if not VOICE_ENABLED:
        raise HTTPException(status_code=503, detail="Voice features are disabled")

    try:
        audio_data = await file.read()
        result = await transcribe(
            audio_data=audio_data,
            filename=file.filename or "audio.wav",
            language=language,
            prompt=prompt,
        )
        return {
            "text": result.text,
            "language": result.language,
            "duration_seconds": result.duration_seconds,
            "segments": result.segments,
            "processing_time_ms": round(result.processing_time_ms, 1),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(..., description="Text to convert to speech (max 4096 chars)"),
    voice: str = Form("nova", description="TTS voice name"),
    speed: float = Form(1.0, ge=0.25, le=4.0, description="Playback speed"),
    response_format: str = Form("mp3", description="Output audio format"),
    _user=Depends(get_current_user),
    _limiter: None = Depends(RateLimiter(times=10, seconds=60)),
):
    """
    Convert text to speech using OpenAI TTS.

    Voices: alloy, echo, fable, onyx, nova, shimmer.
    Formats: mp3, opus, aac, flac, wav, pcm.
    """
    if not VOICE_ENABLED:
        raise HTTPException(status_code=503, detail="Voice features are disabled")

    try:
        result = await synthesize(
            text=text,
            voice=voice,
            speed=speed,
            response_format=response_format,
        )

        media_types = {
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "wav": "audio/wav",
            "pcm": "audio/L16",
        }

        return Response(
            content=result.audio_bytes,
            media_type=media_types.get(result.format, "audio/mpeg"),
            headers={
                "X-Processing-Time-Ms": str(round(result.processing_time_ms, 1)),
                "Content-Disposition": f'inline; filename="speech.{result.format}"',
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/chat")
async def voice_chat(
    file: UploadFile = File(..., description="Audio file with customer question"),
    language: str | None = Form(None, description="ISO-639-1 language hint"),
    voice: str = Form("nova", description="TTS voice for response"),
    text_only: bool = Form(False, description="Return text only (no audio synthesis)"),
    _user=Depends(get_current_user),
    _limiter: None = Depends(RateLimiter(times=5, seconds=60)),
):
    """
    Full voice chat pipeline: Audio → Transcribe → RAG → Synthesize → Audio.

    1. Transcribes the uploaded audio using Whisper
    2. Sends the text to the RAG chain for a response
    3. Synthesizes the response as audio (unless text_only=true)
    4. Returns both text and audio
    """
    if not VOICE_ENABLED:
        raise HTTPException(status_code=503, detail="Voice features are disabled")

    try:
        # Step 1: Transcribe
        audio_data = await file.read()
        transcription = await transcribe(
            audio_data=audio_data,
            filename=file.filename or "audio.wav",
            language=language,
        )

        user_text = transcription.text
        if not user_text.strip():
            return {
                "user_text": "",
                "reply_text": "I couldn't understand the audio. Could you try again?",
                "audio_base64": None,
                "sources": [],
            }

        # Step 2: RAG
        reply_text = ""
        sources = []
        try:
            from packages.llm_engine.chains.rag_chain import RAGChain

            chain = RAGChain()
            result = await chain.generate(user_text)
            reply_text = result.get("reply", "Sorry, I couldn't generate a response.")
            sources = result.get("sources", [])
        except Exception as e:
            logger.warning("RAG chain failed in voice chat, using fallback: %s", e)
            reply_text = (
                "I received your question but I'm having trouble generating a response "
                "right now. Please try again or contact support directly."
            )

        # Step 3: Synthesize (optional)
        audio_base64 = None
        if not text_only:
            try:
                import base64

                synthesis = await synthesize(text=reply_text[:4096], voice=voice)
                audio_base64 = base64.b64encode(synthesis.audio_bytes).decode("utf-8")
            except Exception as e:
                logger.warning("TTS synthesis failed in voice chat: %s", e)

        return {
            "user_text": user_text,
            "reply_text": reply_text,
            "audio_base64": audio_base64,
            "audio_format": "mp3" if audio_base64 else None,
            "sources": sources,
            "transcription_language": transcription.language,
            "transcription_duration_s": transcription.duration_seconds,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/status")
async def voice_status():
    """Check voice feature availability."""
    return {
        "enabled": VOICE_ENABLED,
        "supported_audio_formats": sorted(SUPPORTED_AUDIO_FORMATS),
        "supported_voices": sorted(SUPPORTED_TTS_VOICES),
    }
