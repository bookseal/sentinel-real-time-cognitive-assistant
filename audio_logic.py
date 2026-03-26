# -----------------------------------------------------------------------------
# audio_logic.py — Local Volume Guard for Sentinel
#
# Purpose: Provides zero-cost, zero-latency audio volume analysis using only
#          NumPy. This module is the core of Phase 01's "Local vs. Cloud"
#          strategy: instead of streaming audio to an API ($0.06/min), we
#          compute Root Mean Square (RMS) energy locally ($0.00).
#
# Phase:   01 — Sensory Foundation
# Dependencies: numpy (signal math)
# -----------------------------------------------------------------------------

"""
Audio Logic Module for Sentinel
================================
Local audio analysis functions for volume monitoring.
Zero network overhead — all computation is done with NumPy.
"""

import numpy as np

# -----------------------------------------------------------------------------
# 1. Threshold Constants
#
# Lowered for meeting-room sensitivity: even a slightly raised voice (70 dB)
# should trigger a red alert. Normal conversation is ~55-65 dB in a quiet room.
# Users can adjust sensitivity via the UI slider (multiplier on these values).
# -----------------------------------------------------------------------------
SHOUT_THRESHOLD_DB = 70.0     # Red Alert: raised voice in meeting
WARNING_THRESHOLD_DB = 60.0   # Yellow Warning: slightly elevated volume

# Reference amplitude — maximum value for 16-bit signed integer audio.
# Used as the denominator when converting raw amplitude to 0.0–1.0 range.
REF_AMPLITUDE = 32768.0


# -----------------------------------------------------------------------------
# 2. RMS Calculation — Decibel Scale
#
# The RMS formula measures the "average power" of an audio signal:
#   X_rms = sqrt(1/n * sum(x_i^2))
#
# We then convert to decibels for human-readable thresholds:
#   dB_FS  = 20 * log10(X_rms)         — decibels relative to full scale
#   dB_SPL ≈ dB_FS + 94                — approximate Sound Pressure Level
#
# Why +94? In acoustic engineering, 0 dBFS (digital full scale) corresponds
# roughly to 94 dB SPL (1 Pascal reference). This offset maps our digital
# readings to the physical scale that humans intuitively understand.
# -----------------------------------------------------------------------------
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

    # Use float64 to avoid precision loss during squaring of large int16 values
    audio_f = audio_data.astype(np.float64)

    # Normalize integer audio (e.g., int16 range -32768..32767) to -1.0..1.0
    # This ensures the dB calculation is independent of the input dtype
    if np.issubdtype(audio_data.dtype, np.integer):
        audio_f = audio_f / np.iinfo(audio_data.dtype).max

    # Core RMS: square each sample, take the mean, then square root
    rms = np.sqrt(np.mean(audio_f ** 2))

    # Guard against log(0) which would produce -inf or NaN
    if rms <= 0:
        return float("-inf")

    # Convert to dB scale (0 dB = full scale)
    # Map to approximate SPL: full-scale digital ~= 94 dB SPL reference
    db_fs = 20.0 * np.log10(rms)
    db_spl_approx = db_fs + 94.0  # Approximate SPL mapping

    return float(db_spl_approx)


# -----------------------------------------------------------------------------
# 3. RMS Calculation — Linear Scale
#
# A simplified version that returns raw amplitude (0.0 to 1.0) instead of dB.
# Used by the UI to drive the visual audio level bar, where a linear scale
# provides more intuitive visual feedback than logarithmic dB.
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# 4. Volume Threshold Evaluation — Sliding Window Filter
#
# Instead of triggering alerts on a single audio chunk (which would cause
# flickering alerts from momentary noise spikes), we maintain a sliding
# window of the last 5 dB readings. The alert level is determined by the
# AVERAGE across the window, acting as a low-pass filter on volume readings.
#
# Window size = 5 chunks × 500ms/chunk = 2.5 seconds of smoothing.
# This means: a shout must be sustained for ~1-2 seconds before triggering
# Red Alert, preventing false positives from door slams or coughs.
# -----------------------------------------------------------------------------
def check_volume_threshold(volume_history: list, current_db: float) -> dict:
    """
    Evaluate volume against thresholds using a sliding window.

    Maintains a sliding window of the last 5 chunks to prevent
    single-frame false positives.

    Args:
        volume_history: List of recent dB values (sliding window).
                        This list is mutated in-place (append + pop).
        current_db: Current chunk's dB level.

    Returns:
        Dict with keys:
            - alert_level: "normal" | "warning" | "red_alert"
            - avg_db: Average dB over the window
            - peak_db: Peak dB in the window
            - current_db: The current reading
    """
    # Append new reading and enforce max window size of 5
    volume_history.append(current_db)
    if len(volume_history) > 5:
        volume_history.pop(0)  # Remove oldest reading (FIFO)

    # Filter out -inf values (silence) before averaging — including them
    # would drag the average to -inf and mask genuine loud readings
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

    # 3-state classification based on average volume across the window
    if avg_db >= SHOUT_THRESHOLD_DB:
        alert_level = "red_alert"     # >= 85 dB: shouting detected
    elif avg_db >= WARNING_THRESHOLD_DB:
        alert_level = "warning"       # >= 75 dB: elevated volume
    else:
        alert_level = "normal"        # < 75 dB: conversational

    return {
        "alert_level": alert_level,
        "avg_db": avg_db,
        "peak_db": peak_db,
        "current_db": current_db,
    }


# -----------------------------------------------------------------------------
# 5. Pitch Detection — NumPy FFT
#
# Extracts the fundamental frequency (F0) of speech using FFT.
# Human voice range: 85–400 Hz (male ~120 Hz, female ~210 Hz).
# When someone gets excited or angry, pitch rises by 50–100+ Hz.
# This is a cheap ($0) local signal that complements volume for
# detecting emotional escalation without any cloud API.
# -----------------------------------------------------------------------------
# Average resting pitch by voice type
PITCH_BASELINE_MALE = 120.0    # Hz — typical male speaking voice
PITCH_BASELINE_FEMALE = 210.0  # Hz — typical female speaking voice
PITCH_ELEVATED_OFFSET = 50.0   # Hz — rise that indicates excitement/anger


def get_pitch_hz(audio_data: np.ndarray, sample_rate: int = 16000) -> float:
    """
    Extract fundamental frequency (F0) using FFT peak detection.

    Filters to human voice range (85–400 Hz) and returns the dominant
    frequency. Returns 0.0 for silence or unvoiced segments.

    Args:
        audio_data: Raw audio samples as NumPy array.
        sample_rate: Sample rate in Hz.

    Returns:
        Fundamental frequency in Hz, or 0.0 if undetectable.
    """
    if audio_data is None or len(audio_data) < 256:
        return 0.0

    # Normalize to float
    audio_f = audio_data.astype(np.float64)
    if np.issubdtype(audio_data.dtype, np.integer):
        audio_f = audio_f / np.iinfo(audio_data.dtype).max

    # Apply Hanning window to reduce spectral leakage
    windowed = audio_f * np.hanning(len(audio_f))

    # FFT — only positive frequencies
    fft_mag = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(windowed), 1.0 / sample_rate)

    # Filter to human voice range (85–400 Hz)
    voice_mask = (freqs >= 85) & (freqs <= 400)
    if not voice_mask.any():
        return 0.0

    voice_fft = fft_mag[voice_mask]
    voice_freqs = freqs[voice_mask]

    # Require minimum energy to avoid detecting noise as pitch
    if voice_fft.max() < 0.01:
        return 0.0

    # Peak frequency in voice range
    peak_idx = voice_fft.argmax()
    return float(voice_freqs[peak_idx])
