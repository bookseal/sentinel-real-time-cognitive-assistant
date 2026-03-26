# -----------------------------------------------------------------------------
# app.py — Phase 01: Local Volume Guard (Minimal UI)
#
# Purpose: Stream microphone audio and display real-time volume level in dB.
#          No cloud API calls. No WebSocket. No transcript. Pure local NumPy.
# -----------------------------------------------------------------------------

import logging
from datetime import datetime
from typing import Optional

import gradio as gr
import numpy as np

from audio_buffer import CircularAudioBuffer
from audio_logic import get_rms_db, check_volume_threshold
from vad import VoiceActivityDetector

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sentinel")

TARGET_SAMPLE_RATE = 16000

# ──────────────────────────────────────────────
# Global State
# ──────────────────────────────────────────────
audio_buffer = CircularAudioBuffer(max_chunks=30)
vad: Optional[VoiceActivityDetector] = None

app_state = {
    "vad_active": False,
    "speech_prob": 0.0,
    "rms_level": 0.0,
    "chunks_processed": 0,
    "speech_chunks": 0,
    "last_activity": None,
    "volume_db": 0.0,
    "volume_history": [],
    "volume_alert": "normal",
}


# ──────────────────────────────────────────────
# Audio Helpers
# ──────────────────────────────────────────────
def compute_rms(audio: np.ndarray) -> float:
    if len(audio) == 0:
        return 0.0
    audio_f = audio.astype(np.float32)
    if np.issubdtype(audio.dtype, np.integer):
        audio_f = audio_f / np.iinfo(audio.dtype).max
    return float(np.sqrt(np.mean(audio_f**2)))


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return audio
    ratio = target_sr / orig_sr
    new_length = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, new_length)
    return np.interp(indices, np.arange(len(audio)), audio.astype(np.float32)).astype(
        audio.dtype
    )


# ──────────────────────────────────────────────
# Audio Processing (Volume Guard Only)
# ──────────────────────────────────────────────
def process_audio_chunk(audio_data):
    """Process audio chunk: resample → RMS → dB → threshold → VAD → UI update."""
    global vad

    if audio_data is None:
        return generate_status_html()

    sample_rate, audio = audio_data

    # Stereo → mono
    if audio.ndim > 1:
        audio = audio.mean(axis=1).astype(audio.dtype)

    # Resample to 16kHz
    if sample_rate != TARGET_SAMPLE_RATE:
        audio_16k = resample_audio(audio, sample_rate, TARGET_SAMPLE_RATE)
    else:
        audio_16k = audio

    # RMS (linear)
    rms = compute_rms(audio_16k)
    app_state["rms_level"] = rms
    app_state["chunks_processed"] += 1

    # Volume Guard: dB calculation
    db_level = get_rms_db(audio_16k)
    app_state["volume_db"] = db_level
    vol_result = check_volume_threshold(app_state["volume_history"], db_level)
    app_state["volume_alert"] = vol_result["alert_level"]

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
            audio_buffer.push(audio_16k)

    except Exception as e:
        logger.error(f"Audio processing error: {e}")

    return generate_status_html()


# ──────────────────────────────────────────────
# Dashboard HTML
# ──────────────────────────────────────────────
def generate_status_html() -> str:
    vad_active = app_state["vad_active"]
    speech_prob = app_state["speech_prob"]
    rms = app_state["rms_level"]
    chunks = app_state["chunks_processed"]
    speech_chunks = app_state["speech_chunks"]
    last_activity = app_state["last_activity"] or "—"
    volume_db = app_state["volume_db"]
    volume_alert = app_state["volume_alert"]
    buffer_size = audio_buffer.size
    buffer_cap = audio_buffer.capacity

    # Volume Alert
    if volume_alert == "red_alert":
        vol_alert_color = "#ff1744"
        vol_alert_text = "RED ALERT — SHOUTING DETECTED"
        vol_alert_glow = "0 0 30px #ff1744, 0 0 60px #ff174488"
    elif volume_alert == "warning":
        vol_alert_color = "#ffab00"
        vol_alert_text = "WARNING — Elevated Volume"
        vol_alert_glow = "0 0 15px #ffab00"
    else:
        vol_alert_color = "transparent"
        vol_alert_text = ""
        vol_alert_glow = "none"

    # VAD
    if vad_active:
        vad_color = "#00e676"
        vad_text = "SPEECH DETECTED"
        vad_glow = "0 0 20px #00e676, 0 0 40px #00e67688"
    else:
        vad_color = "#aaa"
        vad_text = "Listening..."
        vad_glow = "none"

    # RMS bar
    rms_pct = min(rms * 500, 100)
    rms_color = "#00e676" if rms_pct < 50 else "#ffab00" if rms_pct < 80 else "#ff1744"

    html = f"""
    <div style="
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, #151a2e 0%, #1e213a 50%, #202a45 100%);
        border-radius: 16px;
        padding: 28px;
        color: #f5f5f5;
        border: 1px solid #4d4f66;
    ">
        <!-- Volume Alert Banner -->
        {"" if volume_alert == "normal" else f'''
        <div style="
            text-align: center;
            padding: 20px;
            margin-bottom: 16px;
            border-radius: 10px;
            background: {vol_alert_color}22;
            border: 2px solid {vol_alert_color};
            box-shadow: {vol_alert_glow};
        ">
            <div style="font-size: 24px; font-weight: 700; color: {vol_alert_color};">
                {vol_alert_text}
            </div>
            <div style="font-size: 14px; color: #ccc; margin-top: 4px;">
                Volume: {volume_db:.1f} dB
            </div>
        </div>
        '''}

        <!-- VAD Status -->
        <div style="
            text-align: center;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 12px;
            background: linear-gradient(135deg, #1a1e35, #242945);
            border: 2px solid {vad_color};
            box-shadow: {vad_glow};
        ">
            <div style="font-size: 24px; font-weight: 700; color: {vad_color};">
                {vad_text}
            </div>
            <div style="font-size: 13px; color: #b0b4c4; margin-top: 6px;">
                Speech Probability: <span style="color: {vad_color}; font-weight: 600;">{speech_prob:.1%}</span>
            </div>
        </div>

        <!-- Volume dB Meter -->
        <div style="margin-bottom: 20px;">
            <div style="display:flex;justify-content:space-between;font-size:14px;color:#d1d5e0;margin-bottom:6px;font-weight:600;">
                <span>Volume (dB SPL)</span>
                <span style="color: {'#ff1744' if volume_db >= 85 else '#ffab00' if volume_db >= 75 else '#00e676'};">
                    {volume_db:.1f} dB
                </span>
            </div>
            <div style="background:#111526;border-radius:8px;height:18px;overflow:hidden;border:1px solid #3a3f5a;">
                <div style="
                    width: {min(max((volume_db - 30) / 70 * 100, 0), 100):.1f}%;
                    height: 100%;
                    background: linear-gradient(90deg,
                        {'#ff174488, #ff1744' if volume_db >= 85 else '#ffab0088, #ffab00' if volume_db >= 75 else '#00e67688, #00e676'});
                    border-radius: 8px;
                    transition: width 0.1s ease;
                "></div>
            </div>
        </div>

        <!-- Audio Level RMS -->
        <div style="margin-bottom: 20px;">
            <div style="display:flex;justify-content:space-between;font-size:13px;color:#a4a9c0;margin-bottom:6px;">
                <span>Audio Level (RMS)</span>
                <span>{rms:.4f}</span>
            </div>
            <div style="background:#111526;border-radius:8px;height:12px;overflow:hidden;border:1px solid #3a3f5a;">
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
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px;">
            <div style="background:#1a1e35;padding:12px;border-radius:10px;border:1px solid #3a3f5a;text-align:center;">
                <div style="font-size:11px;color:#9a9eb5;text-transform:uppercase;letter-spacing:1px;">Chunks</div>
                <div style="font-size:18px;font-weight:600;color:#60a5fa;margin-top:4px;">{chunks}</div>
            </div>
            <div style="background:#1a1e35;padding:12px;border-radius:10px;border:1px solid #3a3f5a;text-align:center;">
                <div style="font-size:11px;color:#9a9eb5;text-transform:uppercase;letter-spacing:1px;">Speech</div>
                <div style="font-size:18px;font-weight:600;color:#34d399;margin-top:4px;">{speech_chunks}</div>
            </div>
            <div style="background:#1a1e35;padding:12px;border-radius:10px;border:1px solid #3a3f5a;text-align:center;">
                <div style="font-size:11px;color:#9a9eb5;text-transform:uppercase;letter-spacing:1px;">Buffer</div>
                <div style="font-size:18px;font-weight:600;color:#e2e8f0;margin-top:4px;">{buffer_size}/{buffer_cap}</div>
            </div>
        </div>

        <!-- Last Activity -->
        <div style="text-align:center;font-size:12px;color:#8b92b0;padding-top:10px;border-top:1px solid #3a3f5a;">
            Last Speech: <span style="color:#cad1e6;">{last_activity}</span>
        </div>
    </div>
    """
    return html


def clear_buffer():
    audio_buffer.clear()
    app_state["chunks_processed"] = 0
    app_state["speech_chunks"] = 0
    app_state["last_activity"] = None
    app_state["volume_history"] = []
    app_state["volume_alert"] = "normal"
    app_state["volume_db"] = 0.0
    return generate_status_html()


# ──────────────────────────────────────────────
# Gradio UI
# ──────────────────────────────────────────────
def build_app() -> gr.Blocks:
    custom_css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .gradio-container {
        font-family: 'Inter', sans-serif !important;
        background: linear-gradient(180deg, #0a0a1a 0%, #111122 100%) !important;
        max-width: 700px !important;
        margin: 0 auto !important;
    }
    .dark { --body-background-fill: #0a0a1a !important; }
    .app-header { text-align: center; padding: 16px 0; }
    .app-header h1 {
        background: linear-gradient(135deg, #ff6b6b, #ffa07a, #ff1744);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2em; font-weight: 700; margin-bottom: 2px;
    }
    .app-header p { color: #a0a5b5; font-size: 0.95em; }
    footer { display: none !important; }
    """

    with gr.Blocks(
        title="Sentinel — Volume Guard",
        css=custom_css,
        theme=gr.themes.Base(primary_hue="red", neutral_hue="slate"),
    ) as app:

        gr.HTML("""
            <div class="app-header">
                <h1>Sentinel</h1>
                <p>Phase 01: Local Volume Guard</p>
            </div>
        """)

        gr.Markdown("### Microphone")
        audio_input = gr.Audio(
            sources=["microphone"],
            streaming=True,
            label="Tap to start recording",
            type="numpy",
        )

        gr.Markdown("### Dashboard")
        status_display = gr.HTML(value=generate_status_html())

        reset_btn = gr.Button("Reset", size="sm")

        # Wiring
        audio_input.stream(
            fn=process_audio_chunk,
            inputs=[audio_input],
            outputs=[status_display],
        )

        reset_btn.click(
            fn=clear_buffer,
            inputs=[],
            outputs=[status_display],
        )

    return app


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting Sentinel Phase 01 — Volume Guard")
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
    )
