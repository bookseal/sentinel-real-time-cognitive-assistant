# -----------------------------------------------------------------------------
# app.py — Phase 00: Minimal Volume Gauge
#
# Purpose: Stream microphone audio and display a real-time volume (dB) gauge.
#          No cloud API. No VAD. No pitch. Pure NumPy RMS only.
# -----------------------------------------------------------------------------

import logging

import gradio as gr
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sentinel")

TARGET_SAMPLE_RATE = 16000

# Thresholds (dB SPL approximation)
WARNING_DB = 60.0
ALERT_DB = 70.0


def compute_volume_db(audio: np.ndarray) -> float:
    """Convert audio samples to approximate dB SPL via RMS."""
    if len(audio) == 0:
        return 0.0
    audio_f = audio.astype(np.float32)
    if np.issubdtype(audio.dtype, np.integer):
        audio_f = audio_f / max(np.iinfo(audio.dtype).max, 1)
    rms = float(np.sqrt(np.mean(audio_f ** 2)))
    if rms < 1e-10:
        return 0.0
    db = 20 * np.log10(rms) + 94  # 0 dBFS ≈ 94 dB SPL
    return max(db, 0.0)


def generate_gauge_html(db: float) -> str:
    """Render a simple volume bar + dB readout."""
    if db >= ALERT_DB:
        color = "#ff1744"
        label = "LOUD"
    elif db >= WARNING_DB:
        color = "#ffab00"
        label = "MODERATE"
    else:
        color = "#00e676"
        label = "QUIET"

    pct = min(max((db - 30) / 70 * 100, 0), 100)

    return f"""
    <div style="
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background: #161b2e;
        border-radius: 14px;
        padding: 22px;
        color: #f5f5f5;
        border: 1px solid #2d3352;
    ">
        <div style="display:flex;justify-content:space-between;font-size:15px;font-weight:700;margin-bottom:8px;">
            <span style="color:#f0f0f5;">VOLUME</span>
            <span style="color:{color};">{db:.1f} dB — {label}</span>
        </div>
        <div style="background:#0d1020;border-radius:8px;height:20px;overflow:hidden;">
            <div style="
                width:{pct:.1f}%;
                height:100%;
                background:{color};
                border-radius:8px;
                transition: width 0.15s ease;
            "></div>
        </div>
    </div>
    """


def process_audio(audio_data):
    """Process a streaming audio chunk and return updated gauge HTML."""
    if audio_data is None:
        return generate_gauge_html(0)

    sample_rate, audio = audio_data

    if audio.ndim > 1:
        audio = audio.mean(axis=1).astype(audio.dtype)

    db = compute_volume_db(audio)
    return generate_gauge_html(db)


def build_app() -> gr.Blocks:
    css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .gradio-container {
        font-family: 'Inter', sans-serif !important;
        background: linear-gradient(180deg, #0a0a1a 0%, #111122 100%) !important;
        max-width: 520px !important;
        margin: 0 auto !important;
    }
    .dark { --body-background-fill: #0a0a1a !important; }
    footer { display: none !important; }
    [data-testid="waveform-x"] { display: none !important; }
    .audio-component .waveform-container { display: none !important; }
    .audio-component canvas { display: none !important; }
    .audio-component .timestamps { display: none !important; }
    .audio-component .error { display: none !important; }
    .audio-component .controls { justify-content: center !important; }
    """

    with gr.Blocks(
        title="Sentinel — Volume Gauge",
        css=css,
        theme=gr.themes.Base(primary_hue="red", neutral_hue="slate"),
    ) as app:

        gr.HTML("""
            <div style="text-align:center;padding:16px 0 8px;">
                <h1 style="
                    background: linear-gradient(135deg, #ff6b6b, #ffa07a, #ff1744);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    font-size: 1.8em; font-weight: 700; margin: 0;
                ">Sentinel</h1>
                <p style="color:#a0a5b5;font-size:0.85em;margin:4px 0 0;">
                    Phase 00 — Volume Gauge
                </p>
            </div>
        """)

        audio_input = gr.Audio(
            sources=["microphone"],
            streaming=True,
            label="Tap to Record",
            type="numpy",
        )

        gauge = gr.HTML(value=generate_gauge_html(0))

        audio_input.stream(
            fn=process_audio,
            inputs=[audio_input],
            outputs=[gauge],
        )

    return app


if __name__ == "__main__":
    logger.info("Starting Sentinel Phase 00 — Minimal Volume Gauge")
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
    )
