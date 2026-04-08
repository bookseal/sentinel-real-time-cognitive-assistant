# vad.py — Voice Activity Detection wrapper (Silero VAD)
#
# Silero VAD: 1.8MB ONNX model, ~1ms per 30ms chunk.
# Detects whether a chunk contains human speech.

import logging
import threading

import numpy as np

logger = logging.getLogger("sentinel.vad")

_vad_model = None
_vad_ready = threading.Event()
_vad_failed = False


def load_vad_model():
    """Load Silero VAD model. Call once at startup."""
    global _vad_model, _vad_failed
    try:
        from silero_vad import load_silero_vad
        _vad_model = load_silero_vad(onnx=True)
        _vad_ready.set()
        logger.info("Silero VAD loaded successfully")
    except Exception as e:
        _vad_failed = True
        _vad_ready.set()
        logger.error("Failed to load Silero VAD: %s", e)


def load_vad_model_background():
    """Load VAD model in a background thread."""
    t = threading.Thread(target=load_vad_model, daemon=True)
    t.start()


def is_ready() -> bool:
    """Check if VAD model is loaded and ready."""
    return _vad_ready.is_set() and not _vad_failed


def has_failed() -> bool:
    """Check if VAD model failed to load."""
    return _vad_failed


def get_speech_prob(chunk_16k: np.ndarray) -> float:
    """Return speech probability for a 16kHz audio chunk.

    Returns float 0.0-1.0. If model not ready, returns -1.0
    to signal caller should use fallback logic.
    """
    if not _vad_ready.is_set():
        return -1.0

    if _vad_failed or _vad_model is None:
        return -1.0

    try:
        import torch
        tensor = torch.FloatTensor(chunk_16k.astype(np.float32))
        prob = _vad_model(tensor, 16000).item()
        return float(prob)
    except Exception as e:
        logger.warning("VAD inference error: %s", e)
        return -1.0
