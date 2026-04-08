"""Tests for vad.py — Silero VAD wrapper."""

import numpy as np
import pytest

import vad as vad_module


class TestVadNotLoaded:
    """Tests when VAD model hasn't been loaded yet."""

    def setup_method(self):
        # Reset module state
        vad_module._vad_model = None
        vad_module._vad_failed = False
        vad_module._vad_ready.clear()

    def test_not_ready_before_load(self):
        assert not vad_module.is_ready()

    def test_speech_prob_returns_negative_when_not_ready(self):
        chunk = np.zeros(480, dtype=np.float32)
        assert vad_module.get_speech_prob(chunk) == -1.0

    def test_has_failed_is_false_before_load(self):
        assert not vad_module.has_failed()


class TestVadFailed:
    """Tests when VAD model failed to load."""

    def setup_method(self):
        vad_module._vad_model = None
        vad_module._vad_failed = True
        vad_module._vad_ready.set()

    def test_not_ready_after_failure(self):
        assert not vad_module.is_ready()

    def test_has_failed_is_true(self):
        assert vad_module.has_failed()

    def test_speech_prob_returns_negative(self):
        chunk = np.zeros(480, dtype=np.float32)
        assert vad_module.get_speech_prob(chunk) == -1.0
