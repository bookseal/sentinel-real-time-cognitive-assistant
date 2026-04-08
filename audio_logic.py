# audio_logic.py — Audio analysis utilities
#
# Extracted from app.py for norminette compliance.
# Pure signal math: RMS, dB conversion. No ML, no I/O.

import numpy as np


def compute_volume_db(audio: np.ndarray) -> float:
    """Convert raw audio samples to decibels (dB).

    Steps:
      1. Normalize int samples → float (-1.0 ~ 1.0)
      2. RMS (Root Mean Square) for average loudness
      3. dB: 20 * log10(rms) + 94 (digital 0 dBFS ~ 94 dB SPL)
    """
    if len(audio) == 0:
        return 0.0

    audio_f = audio.astype(np.float32)
    if np.issubdtype(audio.dtype, np.integer):
        audio_f = audio_f / max(np.iinfo(audio.dtype).max, 1)

    rms = float(np.sqrt(np.mean(audio_f ** 2)))
    if rms < 1e-10:
        return 0.0

    db = 20 * np.log10(rms) + 94
    return max(db, 0.0)


def resample_to_16k(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Resample audio to 16kHz for VAD. Simple linear interpolation."""
    if len(audio) == 0 or sample_rate <= 0:
        return np.array([], dtype=np.float32)
    if sample_rate == 16000:
        return audio.astype(np.float32)
    ratio = 16000 / sample_rate
    new_len = int(len(audio) * ratio)
    if new_len == 0:
        return np.array([], dtype=np.float32)
    indices = np.linspace(0, len(audio) - 1, new_len)
    return np.interp(indices, np.arange(len(audio)), audio.astype(np.float32))
