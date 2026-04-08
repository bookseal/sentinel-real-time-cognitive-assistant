"""Tests for audio_logic.py — RMS/dB computation and resampling."""

import numpy as np
import pytest

from audio_logic import compute_volume_db, resample_to_16k


class TestComputeVolumeDb:
    def test_empty_array(self):
        assert compute_volume_db(np.array([])) == 0.0

    def test_silence(self):
        silence = np.zeros(1600, dtype=np.float32)
        assert compute_volume_db(silence) == 0.0

    def test_near_silence(self):
        """RMS below 1e-10 should return 0, not -inf."""
        tiny = np.full(1600, 1e-12, dtype=np.float32)
        assert compute_volume_db(tiny) == 0.0

    def test_normal_audio_returns_positive_db(self):
        # 0.01 RMS ~ normal speech
        audio = np.random.normal(0, 0.01, 16000).astype(np.float32)
        db = compute_volume_db(audio)
        assert 40 < db < 70

    def test_loud_audio_returns_high_db(self):
        # 0.1 RMS ~ shouting
        audio = np.random.normal(0, 0.1, 16000).astype(np.float32)
        db = compute_volume_db(audio)
        assert db > 70

    def test_integer_audio_normalized(self):
        """int16 audio should be normalized to [-1, 1] before RMS."""
        audio = np.array([1000, -1000, 500, -500], dtype=np.int16)
        db = compute_volume_db(audio)
        assert db > 0

    def test_never_returns_negative(self):
        """dB should never go below 0."""
        tiny = np.full(100, 1e-8, dtype=np.float32)
        assert compute_volume_db(tiny) >= 0.0


class TestResampleTo16k:
    def test_already_16k_returns_same(self):
        audio = np.ones(1600, dtype=np.float32)
        result = resample_to_16k(audio, 16000)
        np.testing.assert_array_equal(result, audio)

    def test_48k_to_16k_shrinks(self):
        audio = np.ones(4800, dtype=np.float32)
        result = resample_to_16k(audio, 48000)
        assert len(result) == 1600

    def test_44100_to_16k(self):
        audio = np.ones(4410, dtype=np.float32)
        result = resample_to_16k(audio, 44100)
        expected_len = int(4410 * 16000 / 44100)
        assert len(result) == expected_len
