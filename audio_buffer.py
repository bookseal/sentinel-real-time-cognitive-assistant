# audio_buffer.py — Ring buffer for VAD-gated utterance collection
#
# Collects voiced audio into complete utterances:
#   - 300ms pre-roll (captures speech onset before VAD fires)
#   - 1.5-2s voiced buffer accumulation
#   - 500ms hangover (trailing syllables after VAD drops)
#   - Utterances < 1s are discarded
#
# If VAD is unavailable, falls back to fixed 2-second intervals.

import collections

import numpy as np

# At 16kHz: 300ms = 4800 samples, 500ms = 8000 samples
SAMPLE_RATE = 16000
PRE_ROLL_MS = 300
HANGOVER_MS = 500
MIN_UTTERANCE_MS = 1000
MAX_UTTERANCE_MS = 5000

_samples = lambda ms: int(SAMPLE_RATE * ms / 1000)


class AudioBuffer:
    """Collects VAD-gated audio into complete utterances."""

    def __init__(self):
        self.reset()
        pre_roll_size = _samples(PRE_ROLL_MS) // _samples(500) + 2
        self._pre_roll = collections.deque(maxlen=max(pre_roll_size, 1))

    def reset(self):
        """Clear buffer state for a new utterance."""
        self._chunks = []
        self._voiced_samples = 0
        self._hangover_samples = 0
        self._in_speech = False

    def feed(self, chunk_16k: np.ndarray, speech_prob: float):
        """Feed a chunk and speech probability. Returns utterance or None.

        Args:
            chunk_16k: Audio chunk at 16kHz
            speech_prob: 0.0-1.0 from VAD, or -1.0 if VAD unavailable
        """
        if speech_prob < 0:
            return self._feed_no_vad(chunk_16k)
        return self._feed_with_vad(chunk_16k, speech_prob)

    def _feed_with_vad(self, chunk, prob):
        is_speech = prob > 0.5
        chunk = chunk.copy()  # prevent mutation by caller

        if not self._in_speech and is_speech:
            self._in_speech = True
            self._hangover_samples = 0
            for old_chunk in self._pre_roll:
                self._chunks.append(old_chunk)
            self._pre_roll.clear()
            self._chunks.append(chunk)
            self._voiced_samples += len(chunk)
            return None

        if self._in_speech and is_speech:
            self._hangover_samples = 0
            self._chunks.append(chunk)
            self._voiced_samples += len(chunk)
            if self._voiced_samples >= _samples(MAX_UTTERANCE_MS):
                return self._emit()
            return None

        if self._in_speech and not is_speech:
            self._chunks.append(chunk)
            self._hangover_samples += len(chunk)
            if self._hangover_samples >= _samples(HANGOVER_MS):
                return self._emit()
            return None

        # Not in speech, no speech detected: just store pre-roll
        self._pre_roll.append(chunk)
        return None

    def _feed_no_vad(self, chunk):
        """Fallback: collect fixed 2-second chunks without VAD gating."""
        if len(chunk) == 0:
            return None
        self._chunks.append(chunk.copy())
        self._voiced_samples += len(chunk)
        if self._voiced_samples >= _samples(2000):
            return self._emit()
        return None

    def _emit(self):
        """Concatenate buffered chunks into an utterance. Reset state."""
        if not self._chunks:
            self.reset()
            return None

        utterance = np.concatenate(self._chunks)
        duration_ms = len(utterance) / SAMPLE_RATE * 1000
        self.reset()

        if duration_ms < MIN_UTTERANCE_MS:
            return None
        return utterance
