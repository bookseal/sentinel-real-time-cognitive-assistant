"""
Audio Logic Module for Sentinel
================================
Local audio analysis functions for volume monitoring.
Zero network overhead — all computation is done with NumPy.
"""

import numpy as np

# Volume threshold in dB for "shouting" detection
SHOUT_THRESHOLD_DB = 85.0
WARNING_THRESHOLD_DB = 75.0

# Reference amplitude for dB calculation (int16 max)
REF_AMPLITUDE = 32768.0


def get_rms_db(audio_data: np.ndarray) -> float:
    """
    Calculate Root Mean Square (RMS) energy of audio in decibels (dB SPL approximation).

    Formula: X_rms = sqrt(1/n * sum(x_i^2))
    dB = 20 * log10(X_rms / ref)

    Args:
        audio_data: Raw audio samples as NumPy array.

    Returns:
        RMS level in decibels. Returns -inf for silence.
    """
    if audio_data is None or len(audio_data) == 0:
        return float("-inf")

    audio_f = audio_data.astype(np.float64)

    # Normalize integer types to float range
    if np.issubdtype(audio_data.dtype, np.integer):
        audio_f = audio_f / np.iinfo(audio_data.dtype).max

    rms = np.sqrt(np.mean(audio_f ** 2))

    if rms <= 0:
        return float("-inf")

    # Convert to dB scale (0 dB = full scale)
    # Map to approximate SPL: full-scale digital ~= 94 dB SPL reference
    db_fs = 20.0 * np.log10(rms)
    db_spl_approx = db_fs + 94.0  # Approximate SPL mapping

    return float(db_spl_approx)


def get_rms_linear(audio_data: np.ndarray) -> float:
    """
    Calculate raw RMS amplitude (0.0 to 1.0 range).

    Args:
        audio_data: Raw audio samples as NumPy array.

    Returns:
        RMS level as a float between 0.0 and 1.0.
    """
    if audio_data is None or len(audio_data) == 0:
        return 0.0

    audio_f = audio_data.astype(np.float64)
    if np.issubdtype(audio_data.dtype, np.integer):
        audio_f = audio_f / np.iinfo(audio_data.dtype).max

    return float(np.sqrt(np.mean(audio_f ** 2)))


def check_volume_threshold(volume_history: list, current_db: float) -> dict:
    """
    Evaluate volume against thresholds using a sliding window.

    Maintains a sliding window of the last 5 chunks to prevent
    single-frame false positives.

    Args:
        volume_history: List of recent dB values (sliding window).
        current_db: Current chunk's dB level.

    Returns:
        Dict with keys:
            - alert_level: "normal" | "warning" | "red_alert"
            - avg_db: Average dB over the window
            - peak_db: Peak dB in the window
            - current_db: The current reading
    """
    # Update sliding window (keep last 5)
    volume_history.append(current_db)
    if len(volume_history) > 5:
        volume_history.pop(0)

    # Filter out -inf values for averaging
    valid_values = [v for v in volume_history if v != float("-inf")]

    if not valid_values:
        return {
            "alert_level": "normal",
            "avg_db": 0.0,
            "peak_db": 0.0,
            "current_db": current_db,
        }

    avg_db = sum(valid_values) / len(valid_values)
    peak_db = max(valid_values)

    # Determine alert level
    if avg_db >= SHOUT_THRESHOLD_DB:
        alert_level = "red_alert"
    elif avg_db >= WARNING_THRESHOLD_DB:
        alert_level = "warning"
    else:
        alert_level = "normal"

    return {
        "alert_level": alert_level,
        "avg_db": avg_db,
        "peak_db": peak_db,
        "current_db": current_db,
    }
