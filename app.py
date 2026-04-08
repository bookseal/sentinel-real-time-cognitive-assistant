# =============================================================================
# app.py — v0.2: VAD-Gated Emotion Detection
#
# Audio pipeline:
#
#   [Browser Mic] --500ms chunks--> [Gradio Stream]
#          |                              |
#          |                     resample to 16kHz
#          |                              |
#          |                     +--------+--------+
#          |                     |                 |
#          |                [Silero VAD]       [RMS/dB]
#          |                speech_prob         volume
#          |                     |                 |
#          |                [AudioBuffer]     gauge logic
#          |                     |
#          |              utterance complete?
#          |                     |
#          |              [OpenAI API]
#          |              emotion label
#          |                     |
#          +<-- HTML gauge + emotion + alert --+
# =============================================================================

import logging
import time

import gradio as gr
import numpy as np

from audio_logic import compute_volume_db, resample_to_16k
from audio_buffer import AudioBuffer
import vad as vad_module
import emotion as emotion_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sentinel")

# =============================================================================
# Constants
# =============================================================================
WARNING_DB = 60.0
ALERT_DB = 70.0
ALERT_DURATION = 10  # seconds


# =============================================================================
# Session State — per-session mutable state, prevents cross-talk
# =============================================================================
class SessionState:
    """Mutable state for one Gradio session."""

    def __init__(self):
        self.alert_until = 0.0
        self.alert_level = ""
        self.buffer = AudioBuffer()
        self.last_emotion = None
        self.emotion_future = None


def get_or_create_state(state_holder):
    """Get existing state or create new one from Gradio state."""
    if state_holder is None:
        return SessionState()
    return state_holder


# =============================================================================
# HTML Gauge — visual output sent to the browser
# =============================================================================
def generate_gauge_html(db: float, state: SessionState) -> str:
    """Return HTML with volume bar + emotion label + alert banner."""
    if db >= ALERT_DB:
        color, label = "red", "LOUD"
    elif db >= WARNING_DB:
        color, label = "orange", "MODERATE"
    else:
        color, label = "green", "QUIET"

    pct = min(max((db - 30) / 70 * 100, 0), 100)

    # Emotion label
    emotion_html = ""
    if state.last_emotion:
        e_colors = {"calm": "#00c853", "stressed": "#ff9100", "angry": "#ff1744"}
        e_color = e_colors.get(state.last_emotion, "#888")
        emotion_html = f"""
        <p style="margin:8px 0;">
            <strong>Emotion:</strong>
            <span style="color:{e_color}; font-weight:bold;
                         text-transform:uppercase;">{state.last_emotion}</span>
        </p>"""

    # Alert banner
    remaining = state.alert_until - time.time()
    banner = ""
    if remaining > 0:
        a_color = "red" if state.alert_level == "red" else "orange"
        a_text = ("ALERT — Voice Too Loud" if a_color == "red"
                  else "CAUTION — Volume Rising")
        banner = f"""
        <div style="padding:12px; margin-bottom:12px; border-radius:8px;
                    background:{a_color}; color:white; text-align:center;">
            <strong>{a_text}</strong>
            <span style="opacity:0.8; margin-left:8px;">
                ({remaining:.0f}s)</span>
        </div>"""

    return f"""
    <div style="padding:16px;">
        {banner}
        <p><strong>Volume:</strong> {db:.1f} dB —
           <span style="color:{color};">{label}</span></p>
        {emotion_html}
        <div style="background:#ddd; border-radius:8px; height:24px;">
            <div style="width:{pct:.1f}%; height:100%; background:{color};
                        border-radius:8px; transition:width 0.15s;">
            </div>
        </div>
    </div>
    """


# =============================================================================
# Audio Processing — Gradio stream callback
# =============================================================================
def process_audio(audio_data, state_holder):
    """Process one audio chunk. Returns (gauge_html, updated_state)."""
    state = get_or_create_state(state_holder)

    if audio_data is None:
        return generate_gauge_html(0, state), state

    sample_rate, audio = audio_data

    # Stereo → Mono
    if audio.ndim > 1:
        audio = audio.mean(axis=1).astype(audio.dtype)

    # Volume (local, fast)
    db = compute_volume_db(audio)

    # Persistent alert logic
    if db >= ALERT_DB:
        state.alert_until = time.time() + ALERT_DURATION
        state.alert_level = "red"
    elif db >= WARNING_DB:
        if state.alert_until - time.time() <= 0 or state.alert_level != "red":
            state.alert_until = time.time() + ALERT_DURATION
            state.alert_level = "yellow"

    # Check if emotion future completed
    if state.emotion_future and state.emotion_future.done():
        try:
            result = state.emotion_future.result()
            if result:
                state.last_emotion = result
        except Exception:
            pass
        state.emotion_future = None

    # VAD + Buffer pipeline (only if VAD module has been initialized)
    audio_16k = resample_to_16k(audio, sample_rate)
    speech_prob = vad_module.get_speech_prob(audio_16k)
    utterance = state.buffer.feed(audio_16k, speech_prob)

    # If we got a complete utterance, submit for emotion classification
    if utterance is not None and state.emotion_future is None:
        state.emotion_future = emotion_module.classify_emotion_async(utterance)

    return generate_gauge_html(db, state), state


# =============================================================================
# Gradio UI
# =============================================================================
def build_app() -> gr.Blocks:
    with gr.Blocks(title="Sentinel — Voice Monitor") as app:
        gr.Markdown("# Sentinel\nv0.2 — VAD + Emotion Detection")

        session_state = gr.State(value=None)

        audio_input = gr.Audio(
            sources=["microphone"],
            streaming=True,
            label="Tap to Record",
            type="numpy",
        )
        gauge = gr.HTML(value=generate_gauge_html(0, SessionState()))

        audio_input.stream(
            fn=process_audio,
            inputs=[audio_input, session_state],
            outputs=[gauge, session_state],
        )

    return app


# =============================================================================
# Entry Point
# =============================================================================
if __name__ == "__main__":
    logger.info("Starting Sentinel v0.2 — VAD + Emotion Detection")

    # Load VAD model in background (app starts instantly)
    vad_module.load_vad_model_background()

    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
    )
