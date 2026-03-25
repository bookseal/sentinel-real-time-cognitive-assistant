"""
Voice Activity Detection (VAD) Module for Sentinel
====================================================
Wraps Silero VAD v5 for real-time speech detection.
Only wakes up downstream processing when human speech is detected.
"""

import numpy as np
import torch


class VoiceActivityDetector:
    """Silero VAD wrapper for real-time speech detection."""

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        """
        Initialize the VAD model.

        Args:
            threshold: Speech probability threshold (0.0 - 1.0).
                       Higher values = more aggressive filtering.
            sample_rate: Expected sample rate. Silero supports 8000 or 16000.
        """
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._silence_count = 0
        self._silence_reset_threshold = 10  # Reset after ~5s of silence

        # Load Silero VAD model
        self.model, self.utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
            trust_repo=True,
        )
        self.model.eval()

    def _preprocess(self, audio_chunk: np.ndarray) -> torch.Tensor:
        """
        Convert incoming audio to 16kHz mono float32 tensor.

        Args:
            audio_chunk: Raw audio data as NumPy array.

        Returns:
            Preprocessed torch.Tensor ready for VAD inference.
        """
        # Ensure float32
        if audio_chunk.dtype != np.float32:
            if np.issubdtype(audio_chunk.dtype, np.integer):
                max_val = np.iinfo(audio_chunk.dtype).max
                audio_chunk = audio_chunk.astype(np.float32) / max_val
            else:
                audio_chunk = audio_chunk.astype(np.float32)

        # Convert to mono if stereo
        if audio_chunk.ndim > 1:
            audio_chunk = audio_chunk.mean(axis=1)

        # Normalize to [-1, 1]
        peak = np.abs(audio_chunk).max()
        if peak > 0:
            audio_chunk = audio_chunk / peak

        tensor = torch.from_numpy(audio_chunk)
        return tensor

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Determine if the audio chunk contains human speech.

        Args:
            audio_chunk: Raw audio data as NumPy array.

        Returns:
            True if speech is detected above threshold.
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            return False

        tensor = self._preprocess(audio_chunk)

        # Silero VAD expects specific chunk sizes (512, 1024, 1536 for 16kHz)
        # Pad or truncate to nearest valid size
        valid_sizes = [512, 1024, 1536]
        chunk_len = len(tensor)

        if chunk_len == 0:
            return False

        # Pick the best valid size
        best_size = min(valid_sizes, key=lambda s: abs(s - chunk_len))

        if chunk_len < best_size:
            tensor = torch.nn.functional.pad(tensor, (0, best_size - chunk_len))
        elif chunk_len > best_size:
            # Process in valid-size windows and take max probability
            max_prob = 0.0
            for i in range(0, chunk_len - best_size + 1, best_size):
                window = tensor[i : i + best_size]
                with torch.no_grad():
                    prob = self.model(window.unsqueeze(0), self.sample_rate).item()
                max_prob = max(max_prob, prob)

            is_detected = max_prob > self.threshold
            self._update_silence_counter(is_detected)
            return is_detected

        with torch.no_grad():
            speech_prob = self.model(tensor.unsqueeze(0), self.sample_rate).item()

        is_detected = speech_prob > self.threshold
        self._update_silence_counter(is_detected)
        return is_detected

    def get_speech_probability(self, audio_chunk: np.ndarray) -> float:
        """
        Get the speech probability for the audio chunk.

        Args:
            audio_chunk: Raw audio data as NumPy array.

        Returns:
            Speech probability between 0.0 and 1.0.
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            return 0.0

        tensor = self._preprocess(audio_chunk)

        valid_sizes = [512, 1024, 1536]
        chunk_len = len(tensor)
        best_size = min(valid_sizes, key=lambda s: abs(s - chunk_len))

        if chunk_len < best_size:
            tensor = torch.nn.functional.pad(tensor, (0, best_size - chunk_len))
        elif chunk_len > best_size:
            tensor = tensor[:best_size]

        with torch.no_grad():
            return self.model(tensor.unsqueeze(0), self.sample_rate).item()

    def _update_silence_counter(self, is_speech: bool) -> None:
        """Update silence counter and reset model state on prolonged silence."""
        if is_speech:
            self._silence_count = 0
        else:
            self._silence_count += 1
            if self._silence_count >= self._silence_reset_threshold:
                self.reset()
                self._silence_count = 0

    def reset(self) -> None:
        """Reset the VAD model's internal state."""
        self.model.reset_states()
