# emotion.py — Emotion classification via OpenAI API
#
# Sends VAD-gated utterance audio to OpenAI for emotion classification.
# Returns one of: "calm", "stressed", "angry", or None on failure.
# Runs in a ThreadPoolExecutor to avoid blocking the Gradio callback.

import base64
import concurrent.futures
import io
import logging
import os
import wave
from typing import Optional

import numpy as np

logger = logging.getLogger("sentinel.emotion")

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
_client = None


def _get_client():
    """Lazy-init OpenAI client."""
    global _client
    if _client is None:
        try:
            from openai import OpenAI
            _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        except Exception as e:
            logger.error("Failed to init OpenAI client: %s", e)
    return _client


def _audio_to_wav_base64(audio_16k: np.ndarray) -> str:
    """Convert 16kHz float32 audio to base64-encoded WAV."""
    clipped = np.clip(audio_16k, -1.0, 1.0)
    clipped = np.nan_to_num(clipped, nan=0.0, posinf=1.0, neginf=-1.0)
    pcm = (clipped * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm.tobytes())
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _classify_sync(audio_16k: np.ndarray) -> Optional[str]:
    """Synchronous emotion classification. Called in executor thread."""
    client = _get_client()
    if client is None:
        return None

    try:
        wav_b64 = _audio_to_wav_base64(audio_16k)
        response = client.chat.completions.create(
            model="gpt-4o-mini-audio-preview",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an emotion classifier. Listen to the audio "
                        "and respond with exactly one word: calm, stressed, "
                        "or angry. Nothing else."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": wav_b64,
                                "format": "wav",
                            },
                        },
                    ],
                },
            ],
            timeout=5,
        )
        label = response.choices[0].message.content.strip().lower()
        if label in ("calm", "stressed", "angry"):
            return label
        logger.warning("Unexpected emotion label: %s", label)
        return _fuzzy_match(label)
    except Exception as e:
        logger.warning("Emotion classification failed: %s", e)
        return None


def _fuzzy_match(label: str) -> Optional[str]:
    """Try to match unexpected labels to our 3 categories."""
    label = label.lower()
    if "angry" in label or "anger" in label or "furious" in label:
        return "angry"
    if "stress" in label or "anxious" in label or "tense" in label:
        return "stressed"
    if "calm" in label or "neutral" in label or "relaxed" in label:
        return "calm"
    return None


def classify_emotion_async(audio_16k: np.ndarray) -> concurrent.futures.Future:
    """Submit emotion classification to background thread. Non-blocking."""
    return _executor.submit(_classify_sync, audio_16k)
