"""Tests for app.py — Gradio stream callback and session state."""

import numpy as np
import pytest

from app import SessionState, process_audio, generate_gauge_html


class TestSessionState:
    def test_initial_state(self):
        state = SessionState()
        assert state.alert_until == 0.0
        assert state.alert_level == ""
        assert state.last_emotion is None
        assert state.emotion_future is None

    def test_independent_sessions(self):
        s1 = SessionState()
        s2 = SessionState()
        s1.last_emotion = "angry"
        assert s2.last_emotion is None


class TestGenerateGaugeHtml:
    def test_quiet_is_green(self):
        state = SessionState()
        html = generate_gauge_html(40, state)
        assert "green" in html
        assert "QUIET" in html

    def test_moderate_is_orange(self):
        state = SessionState()
        html = generate_gauge_html(65, state)
        assert "orange" in html
        assert "MODERATE" in html

    def test_loud_is_red(self):
        state = SessionState()
        html = generate_gauge_html(75, state)
        assert "red" in html
        assert "LOUD" in html

    def test_emotion_label_shown(self):
        state = SessionState()
        state.last_emotion = "angry"
        html = generate_gauge_html(50, state)
        assert "angry" in html.lower()
        assert "Emotion" in html

    def test_no_emotion_label_when_none(self):
        state = SessionState()
        html = generate_gauge_html(50, state)
        assert "Emotion" not in html


class TestProcessAudio:
    def test_none_input(self):
        html, state = process_audio(None, None)
        assert "0.0 dB" in html
        assert isinstance(state, SessionState)

    def test_stereo_to_mono(self):
        stereo = np.random.randn(1600, 2).astype(np.float32)
        audio_data = (16000, stereo)
        html, state = process_audio(audio_data, None)
        assert "dB" in html

    def test_loud_audio_triggers_alert(self):
        # Generate loud audio (high amplitude)
        loud = (np.random.randn(16000) * 0.5).astype(np.float32)
        audio_data = (16000, loud)
        html, state = process_audio(audio_data, None)
        assert state.alert_until > 0 or state.alert_level != ""
