"""
WebSocket Client for OpenAI Realtime API
==========================================
Async WebSocket client that handles bidirectional communication
with the OpenAI Realtime API for speech-to-text and sentiment processing.
"""

import asyncio
import base64
import json
import logging
import os
from enum import Enum
from typing import AsyncGenerator, Callable, Optional

import numpy as np
import websockets

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class RealtimeWSClient:
    """Async WebSocket client for OpenAI Realtime API."""

    REALTIME_URL = "wss://api.openai.com/v1/realtime"
    MODEL = "gpt-4o-realtime-preview-2024-12-17"

    def __init__(
        self,
        api_key: Optional[str] = None,
        on_status_change: Optional[Callable] = None,
    ):
        """
        Initialize the WebSocket client.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            on_status_change: Optional callback when connection status changes.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.on_status_change = on_status_change
        self._ws = None
        self._status = ConnectionStatus.DISCONNECTED
        self._receive_task: Optional[asyncio.Task] = None
        self._transcript_buffer = ""
        self._event_handlers: dict[str, list[Callable]] = {}

    @property
    def status(self) -> ConnectionStatus:
        """Current connection status."""
        return self._status

    @status.setter
    def status(self, new_status: ConnectionStatus):
        self._status = new_status
        if self.on_status_change:
            try:
                self.on_status_change(new_status)
            except Exception as e:
                logger.error(f"Status change callback error: {e}")

    def on(self, event_type: str, handler: Callable) -> None:
        """Register an event handler for a specific event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def _emit(self, event_type: str, data: dict) -> None:
        """Emit an event to registered handlers."""
        for handler in self._event_handlers.get(event_type, []):
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")

    async def connect(self) -> bool:
        """
        Open a WebSocket connection to OpenAI Realtime API.

        Returns:
            True if connection successful, False otherwise.
        """
        if not self.api_key:
            logger.error("No API key provided")
            self.status = ConnectionStatus.ERROR
            return False

        self.status = ConnectionStatus.CONNECTING

        try:
            url = f"{self.REALTIME_URL}?model={self.MODEL}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1",
            }

            try:
                self._ws = await websockets.connect(
                    url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                    max_size=2**24,  # 16MB
                )
            except TypeError:
                self._ws = await websockets.connect(
                    url,
                    extra_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                    max_size=2**24,  # 16MB
                )

            self.status = ConnectionStatus.CONNECTED
            logger.info("Connected to OpenAI Realtime API")

            # Configure the session
            await self._configure_session()

            return True

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            return False

    async def _configure_session(self) -> None:
        """Send session configuration after connecting."""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": (
                    "You are Sentinel, an emotional monitoring assistant. "
                    "Listen to the audio input and transcribe it accurately. "
                    "Monitor for signs of emotional arousal such as anger, "
                    "stress, or aggression in the speaker's voice."
                ),
                "input_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
            },
        }
        await self._send_event(config)
        logger.info("Session configured")

    async def send_audio(self, chunk: np.ndarray) -> bool:
        """
        Send a base64-encoded audio frame to the API.

        Args:
            chunk: Audio data as NumPy array (int16 PCM expected).

        Returns:
            True if sent successfully, False otherwise.
        """
        if self._ws is None or self.status != ConnectionStatus.CONNECTED:
            return False

        try:
            # Convert to int16 PCM if needed
            if chunk.dtype == np.float32:
                pcm_data = (chunk * 32767).astype(np.int16)
            elif chunk.dtype == np.int16:
                pcm_data = chunk
            else:
                pcm_data = chunk.astype(np.int16)

            audio_b64 = base64.b64encode(pcm_data.tobytes()).decode("utf-8")

            event = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64,
            }
            await self._send_event(event)
            return True

        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            return False

    async def _send_event(self, event: dict) -> None:
        """Send a JSON event through the WebSocket."""
        if self._ws:
            await self._ws.send(json.dumps(event))

    async def receive(self) -> AsyncGenerator[dict, None]:
        """
        Async generator yielding server events.

        Yields:
            Dict containing event data from the API.
        """
        if self._ws is None:
            return

        try:
            async for message in self._ws:
                try:
                    event = json.loads(message)
                    event_type = event.get("type", "unknown")

                    # Emit event to handlers
                    await self._emit(event_type, event)

                    yield event

                except json.JSONDecodeError:
                    logger.warning("Received non-JSON message")

        except websockets.ConnectionClosed as e:
            logger.warning(f"Connection closed: {e}")
            self.status = ConnectionStatus.DISCONNECTED
        except Exception as e:
            logger.error(f"Receive error: {e}")
            self.status = ConnectionStatus.ERROR

    async def close(self) -> None:
        """Gracefully close the WebSocket connection."""
        if self._ws:
            try:
                await self._ws.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self._ws = None
                self.status = ConnectionStatus.DISCONNECTED

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self._ws is not None and self.status == ConnectionStatus.CONNECTED
