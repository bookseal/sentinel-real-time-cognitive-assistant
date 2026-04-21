import gradio as gr
import numpy as np
import time

def generate_gauge_html(db):
    """Return HTML with volume bar + color label."""
    if db >= 70:
        color, label = "red", "LOUD"
    elif db >= 60:
        color, label = "orange", "MODERATE"
    else:
        color, label = "green", "QUIET"

    pct = min(max((db - 30) / 70 * 100, 0), 100)

    return f"""
    <div style="padding:16px;">
        <p><strong>Volume:</strong> {db:.1f} dB -
            <span style="color:{color};">{label}</span></p>
        <div style="background:#ddd; border-radius:8px; height:24px;">
            <div style="width:{pct:.1f}%; height:100%; background:{color};
                border-radius:8px; transition:width 0.15s;">
            </div>
        </div>
    </div>
    """

WARNING_DB = 60.0
ALERT_DB = 70.0
ALERT_DURATION = 10

class SessionState:
    def __init__(self):
        self.alert_until = 0.0
        self.alert_level = ""

def compute_volume_db(audio):
    """Convert raw audio samples to decibels (dB)."""
    if len(audio) == 0:
        return 0.0
    
    original_dtype = audio.dtype

    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    
    audio_f = audio.astype(np.float32)
    if np.issubdtype(original_dtype, np.integer):
        audio_f = audio_f / max(np.iinfo(original_dtype).max, 1)

    rms = float(np.sqrt(np.mean(audio_f ** 2)))
    if rms < 1e-10:
        return 0.0
    db = 20 * np.log10(rms) + 94
    return max(db, 0.0)

def process_audio(audio_data, state):
    if state is None:
        state = SessionState()
    if audio_data is None:
        return generate_gauge_html(0), state
    sample_rate, audio = audio_data
    db = compute_volume_db(audio)
    return generate_gauge_html(db), state

with gr.Blocks(title = "Sentinel") as app:
    gr.Markdown("# Sentinel - Volume Monitor")
    audio_input = gr.Audio(sources="microphone", streaming=True, type="numpy")
    output = gr.HTML(value=generate_gauge_html(0))
    session_state = gr.State(value=None)
    audio_input.stream(
        fn=process_audio,
        inputs=[audio_input, session_state],
        outputs=[output, session_state],
    )

if __name__ == "__main__":
    app.launch(share=True)
