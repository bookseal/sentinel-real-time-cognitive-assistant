"""
Circular Audio Buffer for Sentinel
===================================
Thread-safe circular buffer using collections.deque.
Default capacity: 30 chunks (≈15 seconds at 500ms/chunk).
"""

import threading
from collections import deque
from typing import List, Optional

import numpy as np


class CircularAudioBuffer:
    """Thread-safe circular buffer for managing audio chunks."""

    def __init__(self, max_chunks: int = 30):
        """
        Initialize the circular buffer.

        Args:
            max_chunks: Maximum number of audio chunks to store.
                        When full, oldest chunks are automatically discarded.
        """
        self._buffer: deque = deque(maxlen=max_chunks)
        self._lock = threading.Lock()
        self._total_pushed = 0

    def push(self, chunk: np.ndarray) -> None:
        """
        Append a raw audio chunk to the buffer.

        Args:
            chunk: NumPy array containing audio samples.
        """
        with self._lock:
            self._buffer.append(chunk.copy())
            self._total_pushed += 1

    def get_all(self) -> List[np.ndarray]:
        """
        Return a snapshot of all buffered chunks.

        Returns:
            List of NumPy arrays (copies of buffered chunks).
        """
        with self._lock:
            return list(self._buffer)

    def get_latest(self, n: int = 1) -> List[np.ndarray]:
        """
        Return the latest N chunks.

        Args:
            n: Number of recent chunks to retrieve.

        Returns:
            List of NumPy arrays.
        """
        with self._lock:
            items = list(self._buffer)
            return items[-n:] if n <= len(items) else items

    def clear(self) -> None:
        """Flush the buffer, removing all stored chunks."""
        with self._lock:
            self._buffer.clear()

    @property
    def size(self) -> int:
        """Current number of chunks in the buffer."""
        with self._lock:
            return len(self._buffer)

    @property
    def capacity(self) -> int:
        """Maximum capacity of the buffer."""
        return self._buffer.maxlen

    @property
    def total_pushed(self) -> int:
        """Total number of chunks ever pushed (including discarded ones)."""
        with self._lock:
            return self._total_pushed

    def get_concatenated(self) -> Optional[np.ndarray]:
        """
        Return all buffered chunks concatenated into a single array.

        Returns:
            Single NumPy array of all samples, or None if empty.
        """
        with self._lock:
            if not self._buffer:
                return None
            return np.concatenate(list(self._buffer))
