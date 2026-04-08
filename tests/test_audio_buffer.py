"""Tests for audio_buffer.py — ring buffer for utterance collection."""

import numpy as np
import pytest

from audio_buffer import AudioBuffer, SAMPLE_RATE


def _chunk(duration_ms=500):
    """Create a test chunk at 16kHz."""
    return np.random.randn(int(SAMPLE_RATE * duration_ms / 1000)).astype(np.float32)


class TestBufferWithVad:
    def test_no_speech_returns_none(self):
        buf = AudioBuffer()
        result = buf.feed(_chunk(), 0.1)
        assert result is None

    def test_speech_onset_starts_buffering(self):
        buf = AudioBuffer()
        buf.feed(_chunk(), 0.1)  # non-speech (pre-roll)
        result = buf.feed(_chunk(), 0.8)  # speech starts
        assert result is None  # still accumulating

    def test_utterance_emitted_after_hangover(self):
        buf = AudioBuffer()
        # Feed enough speech to exceed 1s minimum
        for _ in range(4):  # 4 * 500ms = 2s of speech
            buf.feed(_chunk(500), 0.9)
        # Hangover: speech drops, wait 500ms
        result = buf.feed(_chunk(500), 0.1)
        # 500ms hangover chunk should trigger emit
        assert result is not None
        assert len(result) > 0

    def test_short_utterance_discarded(self):
        buf = AudioBuffer()
        # Only 200ms of speech (well below 1s minimum)
        buf.feed(_chunk(200), 0.9)
        # Hangover triggers (500ms of non-speech)
        result = buf.feed(_chunk(500), 0.1)
        # Total ~700ms, should be discarded (< 1s)
        assert result is None

    def test_pre_roll_captures_onset(self):
        buf = AudioBuffer()
        pre_roll_chunk = _chunk(500)
        buf.feed(pre_roll_chunk, 0.1)  # stored in pre-roll
        buf.feed(_chunk(500), 0.9)  # speech starts, pre-roll included
        buf.feed(_chunk(500), 0.9)  # more speech
        buf.feed(_chunk(500), 0.9)  # more speech
        result = buf.feed(_chunk(500), 0.1)  # hangover
        assert result is not None
        # Result should be longer than just the speech chunks
        # because pre-roll was included
        assert len(result) > SAMPLE_RATE * 1.5

    def test_buffer_resets_after_emit(self):
        buf = AudioBuffer()
        for _ in range(4):
            buf.feed(_chunk(500), 0.9)
        buf.feed(_chunk(500), 0.1)  # emit
        # Feed new speech
        result = buf.feed(_chunk(500), 0.9)
        assert result is None  # new utterance, still accumulating

    def test_max_utterance_length_forces_emit(self):
        buf = AudioBuffer()
        result = None
        for i in range(20):  # 20 * 500ms = 10s, exceeds 5s max
            result = buf.feed(_chunk(500), 0.9)
            if result is not None:
                break
        assert result is not None


class TestBufferNoVad:
    """When VAD is unavailable (speech_prob=-1), use fixed 2s intervals."""

    def test_emits_at_2_seconds(self):
        buf = AudioBuffer()
        result = None
        for i in range(5):  # 5 * 500ms = 2.5s
            result = buf.feed(_chunk(500), -1.0)
            if result is not None:
                break
        assert result is not None

    def test_does_not_emit_before_2_seconds(self):
        buf = AudioBuffer()
        result = buf.feed(_chunk(500), -1.0)
        assert result is None
        result = buf.feed(_chunk(500), -1.0)
        assert result is None
        result = buf.feed(_chunk(500), -1.0)
        assert result is None
