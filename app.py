# -----------------------------------------------------------------------------
# app.py — Phase 01: Local Volume + Pitch Guard (Minimal UI)
#
# Purpose: Stream microphone audio and display real-time volume (dB) and
#          pitch (Hz) gauges. No cloud API. No WebSocket. Pure local NumPy.
#          Features: sensitivity slider, persistent alerts (5s), vibration.
# -----------------------------------------------------------------------------

import logging
import time
from datetime import datetime
from typing import Optional

import gradio as gr
import numpy as np

from audio_buffer import CircularAudioBuffer
from audio_logic import (
    SHOUT_THRESHOLD_DB,
    WARNING_THRESHOLD_DB,
    PITCH_BASELINE_MALE,
    PITCH_ELEVATED_OFFSET,
    get_rms_db,
    get_rms_linear,
    get_pitch_hz,
    check_volume_threshold,
)
from vad import VoiceActivityDetector

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
    "pitch_hz": 0.0,
    "pitch_history": [],     # Sliding window for pitch smoothing
    "alert_until": 0.0,      # Unix timestamp — alert stays visible until this
    "last_alert_level": "",   # Persisted alert level for display
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
# Audio Processing
# ──────────────────────────────────────────────
def process_audio_chunk(audio_data, sensitivity):
    """Process audio: resample → RMS → dB → pitch → threshold → UI."""
    global vad

    if audio_data is None:
        return generate_status_html()

    sample_rate, audio = audio_data

    if audio.ndim > 1:
        audio = audio.mean(axis=1).astype(audio.dtype)

    if sample_rate != TARGET_SAMPLE_RATE:
        audio_16k = resample_audio(audio, sample_rate, TARGET_SAMPLE_RATE)
    else:
        audio_16k = audio

    # RMS
    rms = compute_rms(audio_16k)
    app_state["rms_level"] = rms
    app_state["chunks_processed"] += 1

    # Volume dB with dynamic threshold (sensitivity slider)
    db_level = get_rms_db(audio_16k)
    app_state["volume_db"] = db_level

    effective_shout = SHOUT_THRESHOLD_DB * sensitivity
    effective_warning = WARNING_THRESHOLD_DB * sensitivity

    vol_result = check_volume_threshold(
        app_state["volume_history"], db_level,
    )
    # Override alert_level with dynamic thresholds
    avg_db = vol_result["avg_db"]
    if avg_db >= effective_shout:
        vol_result["alert_level"] = "red_alert"
    elif avg_db >= effective_warning:
        vol_result["alert_level"] = "warning"
    else:
        vol_result["alert_level"] = "normal"

    app_state["volume_alert"] = vol_result["alert_level"]

    # Persistent alert — keep visible for 5 seconds minimum
    now = time.time()
    if vol_result["alert_level"] in ("warning", "red_alert"):
        app_state["alert_until"] = now + 5.0
        app_state["last_alert_level"] = vol_result["alert_level"]

    # Pitch detection
    pitch = get_pitch_hz(audio_16k, TARGET_SAMPLE_RATE)
    app_state["pitch_hz"] = pitch
    app_state["pitch_history"].append(pitch)
    if len(app_state["pitch_history"]) > 5:
        app_state["pitch_history"].pop(0)

    # VAD
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
# Dashboard HTML — Clean Gauge Style
# ──────────────────────────────────────────────
def generate_status_html() -> str:
    vad_active = app_state["vad_active"]
    speech_prob = app_state["speech_prob"]
    rms = app_state["rms_level"]
    chunks = app_state["chunks_processed"]
    speech_chunks = app_state["speech_chunks"]
    last_activity = app_state["last_activity"] or "—"
    volume_db = app_state["volume_db"]
    pitch_hz = app_state["pitch_hz"]

    # Smoothed pitch
    valid_pitches = [p for p in app_state["pitch_history"] if p > 0]
    avg_pitch = sum(valid_pitches) / len(valid_pitches) if valid_pitches else 0.0

    # Volume color
    vol_color = "#ff1744" if volume_db >= 70 else "#ffab00" if volume_db >= 60 else "#00e676"
    vol_pct = min(max((volume_db - 30) / 70 * 100, 0), 100)

    # Pitch color — green < 170 Hz, yellow 170-250, red > 250
    pitch_color = "#ff1744" if avg_pitch > 250 else "#ffab00" if avg_pitch > 170 else "#00e676"
    pitch_pct = min(max((avg_pitch - 85) / 315 * 100, 0), 100) if avg_pitch > 0 else 0

    # VAD dot
    vad_dot = f'<span style="color:#00e676;">●</span> Speech' if vad_active else '<span style="color:#666;">○</span> Silence'

    # Persistent alert banner (5 second minimum, fade in last 2 seconds)
    now = time.time()
    alert_until = app_state["alert_until"]
    alert_html = ""
    vibrate_js = ""

    if now < alert_until:
        remaining = alert_until - now
        # Fade: full opacity for first 3s, then fade to 0.3 over last 2s
        opacity = 1.0 if remaining > 2.0 else 0.3 + 0.7 * (remaining / 2.0)
        alert_level = app_state["last_alert_level"]

        if alert_level == "red_alert":
            a_color = "#ff1744"
            a_text = "ALERT — Voice Raised"
        else:
            a_color = "#ffab00"
            a_text = "CAUTION — Volume Elevated"

        alert_html = f'''
        <div style="
            text-align: center;
            padding: 14px;
            margin-bottom: 14px;
            border-radius: 10px;
            background: {a_color}18;
            border: 1px solid {a_color}88;
            opacity: {opacity:.2f};
            transition: opacity 0.5s ease;
        ">
            <div style="font-size: 18px; font-weight: 700; color: {a_color};">
                {a_text}
            </div>
            <div style="font-size: 12px; color: #999; margin-top: 2px;">
                {remaining:.0f}s remaining
            </div>
        </div>
        '''
        # Vibrate on mobile (only at start of alert, not every render)
        if remaining > 4.5:
            vibrate_js = '<script>if(navigator.vibrate)navigator.vibrate([200,100,200]);</script>'

    # Purpose reminder: This dashboard monitors vocal volume and pitch
    # in real-time during meetings to detect emotional escalation.
    # All computation is local (NumPy) — zero cloud cost.

    html = f"""
    {vibrate_js}
    <div style="
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background: #161b2e;
        border-radius: 14px;
        padding: 22px;
        color: #f5f5f5;
        border: 1px solid #2d3352;
    ">
        <!-- Purpose banner -->
        <div style="text-align:center;font-size:11px;color:#7a80a0;margin-bottom:14px;letter-spacing:0.5px;">
            Meeting Voice Monitor — Local Analysis Only
        </div>

        {alert_html}

        <!-- Volume Gauge -->
        <div style="margin-bottom: 18px;">
            <div style="display:flex;justify-content:space-between;font-size:14px;font-weight:700;margin-bottom:6px;">
                <span style="color:#f0f0f5;">VOLUME</span>
                <span style="color:{vol_color};font-size:15px;">{volume_db:.1f} dB</span>
            </div>
            <div style="background:#0d1020;border-radius:8px;height:16px;overflow:hidden;">
                <div style="width:{vol_pct:.1f}%;height:100%;background:{vol_color};border-radius:8px;"></div>
            </div>
        </div>

        <!-- Pitch Gauge -->
        <div style="margin-bottom: 18px;">
            <div style="display:flex;justify-content:space-between;font-size:14px;font-weight:700;margin-bottom:6px;">
                <span style="color:#f0f0f5;">PITCH</span>
                <span style="color:{pitch_color};font-size:15px;">{avg_pitch:.0f} Hz</span>
            </div>
            <div style="background:#0d1020;border-radius:8px;height:16px;overflow:hidden;">
                <div style="width:{pitch_pct:.1f}%;height:100%;background:{pitch_color};border-radius:8px;"></div>
            </div>
        </div>

        <!-- VAD + Stats -->
        <div style="
            display:flex;
            justify-content:space-between;
            align-items:center;
            font-size:12px;
            color:#9da3bf;
            padding:10px 0 0;
            border-top:1px solid #252a40;
        ">
            <span>{vad_dot} <span style="color:#777;">({speech_prob:.0%})</span></span>
            <span>Chunks <span style="color:#8ab4f8;">{chunks}</span></span>
            <span>Speech <span style="color:#81c995;">{speech_chunks}</span></span>
            <span style="color:#bbb;">{last_activity}</span>
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
    app_state["pitch_hz"] = 0.0
    app_state["pitch_history"] = []
    app_state["alert_until"] = 0.0
    app_state["last_alert_level"] = ""
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
        max-width: 600px !important;
        margin: 0 auto !important;
    }
    .dark { --body-background-fill: #0a0a1a !important; }
    .app-header { text-align: center; padding: 12px 0 8px; }
    .app-header h1 {
        background: linear-gradient(135deg, #ff6b6b, #ffa07a, #ff1744);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.8em; font-weight: 700; margin-bottom: 0;
    }
    .app-header p { color: #a0a5b5; font-size: 0.85em; margin-top: 2px; }
    footer { display: none !important; }

    /* Suppress audio component flicker during streaming.
       Gradio 6.x re-renders the waveform SVG on every chunk,
       causing visual flicker. We hide the waveform entirely
       and keep only the record button. */
    [data-testid="waveform-x"] { display: none !important; }
    .audio-component .timestamps { display: none !important; }
    .audio-component .waveform-container { display: none !important; }
    .audio-component canvas { display: none !important; }
    /* Hide false "microphone not found" warning */
    .audio-component .error { display: none !important; }
    /* Minimize visual noise from the audio box */
    .audio-component .controls { justify-content: center !important; }
    .audio-component .component-wrapper {
        min-height: auto !important;
        padding: 8px !important;
    }
    """

    with gr.Blocks(
        title="Sentinel — Volume Guard",
        css=custom_css,
        theme=gr.themes.Base(primary_hue="red", neutral_hue="slate"),
    ) as app:

        gr.HTML("""
            <div class="app-header">
                <h1>Sentinel</h1>
                <p>Phase 01 — Volume + Pitch Guard</p>
            </div>
        """)

        audio_input = gr.Audio(
            sources=["microphone"],
            streaming=True,
            label="Tap to Record",
            type="numpy",
        )

        status_display = gr.HTML(value=generate_status_html())

        sensitivity = gr.Slider(
            minimum=0.5,
            maximum=2.0,
            value=1.0,
            step=0.1,
            label="Sensitivity (0.5 = very sensitive, 2.0 = noisy environment)",
        )

        reset_btn = gr.Button("Reset", size="sm")

        # Wiring — sensitivity slider is an input to process_audio_chunk
        audio_input.stream(
            fn=process_audio_chunk,
            inputs=[audio_input, sensitivity],
            outputs=[status_display],
        )

        reset_btn.click(
            fn=clear_buffer,
            inputs=[],
            outputs=[status_display],
        )

    return app


if __name__ == "__main__":
    logger.info("Starting Sentinel Phase 01 — Volume + Pitch Guard")
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
    )
