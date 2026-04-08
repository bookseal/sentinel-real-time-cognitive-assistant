"""Tests for emotion.py — OpenAI emotion classification."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from emotion import _classify_sync, _fuzzy_match, _audio_to_wav_base64


class TestFuzzyMatch:
    def test_angry_variants(self):
        assert _fuzzy_match("angry") == "angry"
        assert _fuzzy_match("anger") == "angry"
        assert _fuzzy_match("furious") == "angry"

    def test_stressed_variants(self):
        assert _fuzzy_match("stressed") == "stressed"
        assert _fuzzy_match("anxious") == "stressed"
        assert _fuzzy_match("tense") == "stressed"

    def test_calm_variants(self):
        assert _fuzzy_match("calm") == "calm"
        assert _fuzzy_match("neutral") == "calm"
        assert _fuzzy_match("relaxed") == "calm"

    def test_unknown_returns_none(self):
        assert _fuzzy_match("happy") is None
        assert _fuzzy_match("confused") is None


class TestAudioToWavBase64:
    def test_produces_valid_base64(self):
        audio = np.zeros(16000, dtype=np.float32)
        result = _audio_to_wav_base64(audio)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_different_audio_different_output(self):
        silence = np.zeros(16000, dtype=np.float32)
        noise = np.random.randn(16000).astype(np.float32)
        assert _audio_to_wav_base64(silence) != _audio_to_wav_base64(noise)


class TestClassifySync:
    @patch("emotion._get_client")
    def test_returns_valid_label(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "angry"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        audio = np.random.randn(16000).astype(np.float32)
        result = _classify_sync(audio)
        assert result == "angry"

    @patch("emotion._get_client")
    def test_returns_none_on_api_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_get_client.return_value = mock_client

        audio = np.random.randn(16000).astype(np.float32)
        result = _classify_sync(audio)
        assert result is None

    def test_returns_none_when_no_client(self):
        with patch("emotion._get_client", return_value=None):
            audio = np.random.randn(16000).astype(np.float32)
            result = _classify_sync(audio)
            assert result is None

    @patch("emotion._get_client")
    def test_fuzzy_matches_unexpected_label(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "The speaker sounds furious"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        audio = np.random.randn(16000).astype(np.float32)
        result = _classify_sync(audio)
        assert result == "angry"
