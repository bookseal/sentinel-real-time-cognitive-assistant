"""
Sentinel: Real-time Cognitive Assistant — Phase 1 Application
==============================================================
Gradio streaming audio application with VAD, circular buffer,
and OpenAI Realtime API WebSocket integration.
"""

import asyncio
import logging
import os
import threading
import time
from datetime import datetime

import gradio as gr
import numpy as np
from dotenv import load_dotenv

from audio_buffer import CircularAudioBuffer
from vad import VoiceActivityDetector
from ws_client import ConnectionStatus, RealtimeWSClient

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sentinel")

TARGET_SAMPLE_RATE = 16000

from typing import Optional

# ──────────────────────────────────────────────
# Global State
# ──────────────────────────────────────────────
audio_buffer = CircularAudioBuffer(max_chunks=30)
vad: Optional[VoiceActivityDetector] = None
ws_client: Optional[RealtimeWSClient] = None

# Shared state for UI updates
app_state = {
    "vad_active": False,
    "speech_prob": 0.0,
    "rms_level": 0.0,
    "connection_status": "disconnected",
    "transcript": "",
    "chunks_processed": 0,
    "speech_chunks": 0,
    "last_activity": None,
    "emotion_score": 0.0,
    "ws_loop": None,
    "ws_thread": None,
}


def compute_rms(audio: np.ndarray) -> float:
    """Compute RMS (root mean square) level of audio."""
    if len(audio) == 0:
        return 0.0
    audio_f = audio.astype(np.float32)
    if np.issubdtype(audio.dtype, np.integer):
        audio_f = audio_f / np.iinfo(audio.dtype).max
    return float(np.sqrt(np.mean(audio_f**2)))


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Simple resampling via linear interpolation."""
    if orig_sr == target_sr:
        return audio
    ratio = target_sr / orig_sr
    new_length = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, new_length)
    return np.interp(indices, np.arange(len(audio)), audio.astype(np.float32)).astype(
        audio.dtype
    )


# ──────────────────────────────────────────────
# WebSocket Background Loop
# ──────────────────────────────────────────────
def run_ws_loop(loop: asyncio.AbstractEventLoop):
    """Run the asyncio event loop in a background thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


async def ws_receive_loop():
    """Background task to receive WebSocket events."""
    global ws_client
    if ws_client is None or not ws_client.is_connected:
        return

    try:
        async for event in ws_client.receive():
            event_type = event.get("type", "")

            if event_type == "conversation.item.input_audio_transcription.completed":
                transcript = event.get("transcript", "")
                if transcript:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    app_state["transcript"] += f"[{timestamp}] {transcript}\n"
                    logger.info(f"Transcript: {transcript}")

            elif event_type == "response.audio_transcript.delta":
                delta = event.get("delta", "")
                if delta:
                    app_state["transcript"] += delta

            elif event_type == "response.function_call_arguments.done":
                if event.get("name") == "report_emotion":
                    try:
                        args = json.loads(event.get("arguments", "{}"))
                        if "score" in args:
                            app_state["emotion_score"] = float(args["score"])
                            logger.info(f"Emotion Score Updated: {app_state['emotion_score']}")
                    except Exception as e:
                        logger.error(f"Failed to parse emotion score: {e}")

            elif event_type == "error":
                error = event.get("error", {})
                logger.error(f"API Error: {error}")

    except Exception as e:
        logger.error(f"Receive loop error: {e}")


async def connect_ws():
    """Connect to OpenAI Realtime API."""
    global ws_client
    ws_client = RealtimeWSClient()
    success = await ws_client.connect()
    if success:
        app_state["connection_status"] = "connected"
        logger.info("WebSocket connected successfully")
        # Start receive loop
        asyncio.ensure_future(ws_receive_loop())
    else:
        app_state["connection_status"] = "error"
        logger.error("WebSocket connection failed")
    return success


async def disconnect_ws():
    """Disconnect from OpenAI Realtime API."""
    global ws_client
    if ws_client:
        await ws_client.close()
    app_state["connection_status"] = "disconnected"


async def send_audio_to_ws(chunk: np.ndarray):
    """Send audio chunk to WebSocket."""
    global ws_client
    if ws_client and ws_client.is_connected:
        await ws_client.send_audio(chunk)


# ──────────────────────────────────────────────
# Audio Processing Callback
# ──────────────────────────────────────────────
def process_audio_chunk(audio_data):
    """
    Process incoming audio chunk from Gradio streaming.

    Pipeline: chunk → VAD filter → buffer → WebSocket send
    """
    global vad

    if audio_data is None:
        return generate_status_html(), get_transcript()

    sample_rate, audio = audio_data

    # Convert stereo to mono
    if audio.ndim > 1:
        audio = audio.mean(axis=1).astype(audio.dtype)

    # Resample to 16kHz for VAD
    if sample_rate != TARGET_SAMPLE_RATE:
        audio_16k = resample_audio(audio, sample_rate, TARGET_SAMPLE_RATE)
    else:
        audio_16k = audio

    # Compute RMS level
    rms = compute_rms(audio_16k)
    app_state["rms_level"] = rms
    app_state["chunks_processed"] += 1

    # VAD check
    try:
        if vad is None:
            vad = VoiceActivityDetector(threshold=0.5, sample_rate=TARGET_SAMPLE_RATE)
            logger.info("VAD model loaded")

        is_speech = vad.is_speech(audio_16k)
        speech_prob = vad.get_speech_probability(audio_16k)
        app_state["vad_active"] = is_speech
        app_state["speech_prob"] = speech_prob

        if is_speech:
            app_state["speech_chunks"] += 1
            app_state["last_activity"] = datetime.now().strftime("%H:%M:%S")

            # Push to circular buffer
            audio_buffer.push(audio_16k)

            # Send to WebSocket if connected
            if app_state.get("ws_loop"):
                asyncio.run_coroutine_threadsafe(
                    send_audio_to_ws(audio_16k), app_state["ws_loop"]
                )

    except Exception as e:
        logger.error(f"Audio processing error: {e}")

    return generate_status_html(), get_transcript()


# ──────────────────────────────────────────────
# UI Generation
# ──────────────────────────────────────────────
def generate_status_html() -> str:
    """Generate the real-time status dashboard HTML."""
    vad_active = app_state["vad_active"]
    speech_prob = app_state["speech_prob"]
    rms = app_state["rms_level"]
    conn_status = app_state["connection_status"]
    chunks = app_state["chunks_processed"]
    speech_chunks = app_state["speech_chunks"]
    last_activity = app_state["last_activity"] or "—"
    emotion_score = app_state["emotion_score"]
    buffer_size = audio_buffer.size
    buffer_cap = audio_buffer.capacity

    # VAD indicator
    if vad_active:
        vad_color = "#00e676"
        vad_text = "🎙️ SPEECH DETECTED"
        vad_glow = "0 0 20px #00e676, 0 0 40px #00e67688"
    else:
        vad_color = "#aaa"
        vad_text = "🔇 Listening..."
        vad_glow = "none"

    # Connection indicator
    conn_colors = {
        "connected": ("#00e676", "🟢"),
        "connecting": ("#ffab00", "🟡"),
        "disconnected": ("#aaa", "⚪"),
        "error": ("#ff1744", "🔴"),
    }
    conn_color, conn_icon = conn_colors.get(conn_status, ("#aaa", "⚪"))

    # RMS bar (0 to 100%)
    rms_pct = min(rms * 500, 100)  # Scale for visibility
    rms_color = "#00e676" if rms_pct < 50 else "#ffab00" if rms_pct < 80 else "#ff1744"

    # Emotion Gauge Bar Update
    emotion_pct = min(max(emotion_score * 100, 0), 100)
    # Emotion color transitions from green (0) to yellow (50) to red (100)
    emotion_color = "#00e676" if emotion_pct < 40 else "#ffab00" if emotion_pct < 75 else "#ff1744"

    html = f"""
    <div style="
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, #151a2e 0%, #1e213a 50%, #202a45 100%);
        border-radius: 16px;
        padding: 28px;
        color: #f5f5f5;
        border: 1px solid #4d4f66;
    ">
        <!-- VAD Status -->
        <div style="
            text-align: center;
            padding: 24px;
            margin-bottom: 20px;
            border-radius: 12px;
            background: linear-gradient(135deg, #1a1e35, #242945);
            border: 2px solid {vad_color};
            box-shadow: {vad_glow};
            transition: all 0.3s ease;
        ">
            <div style="font-size: 28px; font-weight: 700; color: {vad_color};">
                {vad_text}
            </div>
            <div style="font-size: 14px; color: #b0b4c4; margin-top: 8px;">
                Speech Probability: <span style="color: {vad_color}; font-weight: 600;">
                    {speech_prob:.1%}
                </span>
            </div>
        </div>

        <!-- Emotion Gauge -->
        <div style="margin-bottom: 20px;">
            <div style="
                display: flex;
                justify-content: space-between;
                font-size: 14px;
                font-weight: 600;
                color: #d1d5e0;
                margin-bottom: 6px;
            ">
                <span>🧠 Emotional Arousal</span>
                <span style="color: {emotion_color};">{emotion_pct:.1f}%</span>
            </div>
            <div style="
                background: #111526;
                border-radius: 8px;
                height: 18px;
                overflow: hidden;
                border: 1px solid #3a3f5a;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
            ">
                <div style="
                    width: {emotion_pct:.1f}%;
                    height: 100%;
                    background: linear-gradient(90deg, {emotion_color}aa, {emotion_color});
                    border-radius: 8px;
                    transition: width 0.3s ease-out, background 0.3s;
                "></div>
            </div>
        </div>

        <!-- Audio Level Meter -->
        <div style="margin-bottom: 24px;">
            <div style="
                display: flex;
                justify-content: space-between;
                font-size: 13px;
                color: #a4a9c0;
                margin-bottom: 6px;
            ">
                <span>📊 Audio Level (RMS)</span>
                <span>{rms:.4f}</span>
            </div>
            <div style="
                background: #111526;
                border-radius: 8px;
                height: 14px;
                overflow: hidden;
                border: 1px solid #3a3f5a;
            ">
                <div style="
                    width: {rms_pct:.1f}%;
                    height: 100%;
                    background: linear-gradient(90deg, {rms_color}88, {rms_color});
                    border-radius: 8px;
                    transition: width 0.1s ease;
                "></div>
            </div>
        </div>

        <!-- Stats Grid -->
        <div style="
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        ">
            <div style="
                background: #1a1e35;
                padding: 14px;
                border-radius: 10px;
                border: 1px solid #3a3f5a;
            ">
                <div style="font-size: 12px; color: #9a9eb5; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                    Connection
                </div>
                <div style="font-size: 16px; font-weight: 500; margin-top: 4px; color: {conn_color};">
                    {conn_icon} {conn_status.upper()}
                </div>
            </div>
            <div style="
                background: #1a1e35;
                padding: 14px;
                border-radius: 10px;
                border: 1px solid #3a3f5a;
            ">
                <div style="font-size: 12px; color: #9a9eb5; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                    Buffer
                </div>
                <div style="font-size: 16px; font-weight: 500; margin-top: 4px;">
                    📦 <span style="color: #e2e8f0;">{buffer_size}/{buffer_cap}</span>
                </div>
            </div>
            <div style="
                background: #1a1e35;
                padding: 14px;
                border-radius: 10px;
                border: 1px solid #3a3f5a;
            ">
                <div style="font-size: 12px; color: #9a9eb5; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                    Chunks Processed
                </div>
                <div style="font-size: 16px; font-weight: 500; margin-top: 4px;">
                    🔢 <span style="color: #60a5fa;">{chunks}</span>
                </div>
            </div>
            <div style="
                background: #1a1e35;
                padding: 14px;
                border-radius: 10px;
                border: 1px solid #3a3f5a;
            ">
                <div style="font-size: 12px; color: #9a9eb5; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                    Speech Chunks
                </div>
                <div style="font-size: 16px; font-weight: 500; margin-top: 4px;">
                    🗣️ <span style="color: #34d399;">{speech_chunks}</span>
                </div>
            </div>
        </div>

        <!-- Last Activity -->
        <div style="
            text-align: center;
            font-size: 13px;
            color: #8b92b0;
            padding-top: 12px;
            border-top: 1px solid #3a3f5a;
            font-weight: 500;
        ">
            Last Speech Activity: <span style="color: #cad1e6;">{last_activity}</span>
        </div>
    </div>
    """
    return html


def get_transcript():
    """Return the current transcript."""
    return app_state["transcript"] or "*Waiting for speech...*"


def connect_action():
    """Handle connect button click."""
    if app_state.get("ws_loop") is None:
        loop = asyncio.new_event_loop()
        app_state["ws_loop"] = loop
        t = threading.Thread(target=run_ws_loop, args=(loop,), daemon=True)
        t.start()
        app_state["ws_thread"] = t

    app_state["connection_status"] = "connecting"
    future = asyncio.run_coroutine_threadsafe(connect_ws(), app_state["ws_loop"])

    try:
        success = future.result(timeout=10)
        if success:
            return "✅ Connected to OpenAI Realtime API", generate_status_html(), get_transcript()
        else:
            return "❌ Connection failed. Check API key.", generate_status_html(), get_transcript()
    except Exception as e:
        app_state["connection_status"] = "error"
        return f"❌ Error: {str(e)}", generate_status_html(), get_transcript()


def disconnect_action():
    """Handle disconnect button click."""
    if app_state.get("ws_loop"):
        asyncio.run_coroutine_threadsafe(disconnect_ws(), app_state["ws_loop"])
    return "⚪ Disconnected", generate_status_html(), get_transcript()


def clear_transcript():
    """Clear the transcript buffer."""
    app_state["transcript"] = ""
    return "*Transcript cleared.*"


def clear_buffer():
    """Clear the audio buffer and reset stats."""
    audio_buffer.clear()
    app_state["chunks_processed"] = 0
    app_state["speech_chunks"] = 0
    app_state["emotion_score"] = 0.0
    app_state["last_activity"] = None
    return generate_status_html(), get_transcript()


# ──────────────────────────────────────────────
# Gradio UI
# ──────────────────────────────────────────────
def build_app() -> gr.Blocks:
    """Build the Gradio application."""

    custom_css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .gradio-container {
        font-family: 'Inter', sans-serif !important;
        background: linear-gradient(180deg, #0a0a1a 0%, #111122 100%) !important;
        max-width: 900px !important;
        margin: 0 auto !important;
    }

    .dark {
        --body-background-fill: #0a0a1a !important;
    }

    .app-header {
        text-align: center;
        padding: 20px 0;
    }

    .app-header h1 {
        background: linear-gradient(135deg, #ff6b6b, #ffa07a, #ff1744);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2em;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .app-header p {
        color: #a0a5b5;
        font-size: 1.05em;
    }

    /* Enhance markdown contrast */
    .gradio-container .markdown-text {
        color: #e2e8f0 !important;
        font-size: 1.05em;
        line-height: 1.6;
    }

    .gradio-container h3, .gradio-container .markdown-text h3 {
        color: #e2e8f0 !important;
        font-weight: 600;
    }

    footer { display: none !important; }
    """

    with gr.Blocks(
        title="🛡️ Sentinel — Real-time Cognitive Assistant",
        css=custom_css,
        theme=gr.themes.Base(
            primary_hue="red",
            neutral_hue="slate",
        ),
    ) as app:

        # Header
        gr.HTML("""
            <div class="app-header">
                <h1>🛡️ Sentinel</h1>
                <p>Real-time Cognitive Assistant — Phase 1: Sensory Input Layer</p>
            </div>
        """)

        # WebSocket Connection
        gr.Markdown("### 🔌 Connection")
        with gr.Row():
            connect_btn = gr.Button(
                "🟢 Connect", variant="primary", size="sm"
            )
            disconnect_btn = gr.Button(
                "🔴 Disconnect", variant="secondary", size="sm"
            )
        conn_msg = gr.Textbox(
            label="Status",
            value="⚪ Disconnected",
            interactive=False,
            lines=1,
        )

        # Audio Input
        gr.Markdown("### 🎤 Audio Input")
        audio_input = gr.Audio(
            sources=["microphone"],
            streaming=True,
            label="Microphone",
            type="numpy",
        )

        # Actions
        gr.Markdown("### ⚡ Actions")
        with gr.Row():
            clear_trans_btn = gr.Button("🗑️ Clear Transcript", size="sm")
            clear_buf_btn = gr.Button("🔄 Reset Buffer", size="sm")

        # Status Dashboard
        gr.Markdown("### 📊 Real-time Dashboard")
        status_display = gr.HTML(value=generate_status_html())

        # Transcript
        gr.Markdown("### 📝 Transcript")
        transcript_display = gr.Markdown(
            value="*Waiting for speech...*",
        )

        # ── Event Wiring ──
        audio_input.stream(
            fn=process_audio_chunk,
            inputs=[audio_input],
            outputs=[status_display, transcript_display],
        )

        connect_btn.click(
            fn=connect_action,
            inputs=[],
            outputs=[conn_msg, status_display, transcript_display],
        )

        disconnect_btn.click(
            fn=disconnect_action,
            inputs=[],
            outputs=[conn_msg, status_display, transcript_display],
        )

        clear_trans_btn.click(
            fn=clear_transcript,
            inputs=[],
            outputs=[transcript_display],
        )

        clear_buf_btn.click(
            fn=clear_buffer,
            inputs=[],
            outputs=[status_display, transcript_display],
        )

    return app


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting Sentinel Phase 1...")
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
