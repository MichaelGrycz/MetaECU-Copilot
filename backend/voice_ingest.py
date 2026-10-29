"""
Voice Command Ingestion: tuner voice note -> calibration intent text.

Two honest paths, both reported to the UI:
1. Browser speech-to-text (Web Speech API) happens in the browser; the text is
   POSTed to the cockpit and translated to an intent by Meta Muse.
2. Audio file upload: if a Whisper-compatible transcription is configured
   (WHISPER_API_KEY + WHISPER_API_BASE_URL env), the audio is transcribed via
   that API; otherwise the endpoint returns a clear 503 telling the user to
   use the browser microphone instead. No fake transcription is performed.

``translate_intent`` uses Muse Spark to convert free speech (PL/EN) into a
normalised engineering intent; with no Meta key it returns the raw text.
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def transcribe_audio(audio_bytes: bytes, filename: str) -> dict:
    key = os.getenv("WHISPER_API_KEY", "")
    base = os.getenv("WHISPER_API_BASE_URL", "")
    if not key or not base:
        return {
            "ok": False,
            "error": (
                "Serwerowa transkrypcja audio nie jest skonfigurowana "
                "(WHISPER_API_KEY / WHISPER_API_BASE_URL). Użyj mikrofonu "
                "przeglądarki (Web Speech API) albo wgraj tekst intencji."
            ),
        }
    import io

    from openai import OpenAI

    client = OpenAI(api_key=key, base_url=base)
    buf = io.BytesIO(audio_bytes)
    buf.name = filename or "note.webm"
    result = client.audio.transcriptions.create(model="whisper-1", file=buf)
    text = (
        result.get("text") if isinstance(result, dict) else getattr(result, "text", "")
    )
    return {"ok": True, "text": text, "source": "whisper_api"}


def translate_intent(spoken_text: str) -> dict:
    """Normalise free tuner speech into an engineering intent via Muse Spark."""
    api_key = os.getenv("META_API_KEY", "")
    if not api_key or api_key.startswith("LLM_...") or not spoken_text.strip():
        return {"intent": spoken_text, "source": "raw_text"}
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("META_API_BASE_URL", "https://api.meta.ai/v1"),
        )
        resp = client.chat.completions.create(
            model=os.getenv("META_MODEL", "muse-spark-1.3"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You convert a tuner's spoken note (Polish or English) into one "
                        "short English calibration intent for an ECU planner. Keep any "
                        "numbers (Nm, rpm). Reply with the intent sentence only."
                    ),
                },
                {"role": "user", "content": spoken_text},
            ],
            max_tokens=2000,
        )
        msg = resp.choices[0].message
        content = (
            msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        )
        if content and content.strip():
            return {"intent": content.strip(), "source": "muse"}
    except Exception:
        pass
    return {"intent": spoken_text, "source": "raw_text"}
