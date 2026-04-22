import time
import gradio as gr
import numpy as np

WARNING_DB = 60.0
ALERT_DB = 70.0
ALERT_DURATION = 10

class SessionState:
    def __init__(self):
        self.alert_until = 0.0
        self.alert_level = ""

def generate_gauge_html(db, state=None):
    """Return HTML with volume bar + color label."""
    if db >= ALERT_DB:
        color, label = "red", "LOUD"
    elif db >= WARNING_DB:
        color, label = "orange", "MODERATE"
    else:
        color, label = "green", "QUIET"

    pct = min(max((db - 30) / 70 * 100, 0), 100)

    banner = ""
    if state and state.alert_until - time.time() > 0:
        remaining = state.alert_until - time.time()
        a_color = "red" if state.alert_level == "red" else "orange"
        a_text = ("ALERT - Voice Too Loud" if a_color == "red"
                else "CAUTION - Volume Rising")
        banner = f"""
        <div style="padding:12px; margin-bottom:12px; border-radius:8px;
            background:{a_color}; color:white; text-align:center;">
            <strong>{a_text}</strong>
            <span style="opacity:0.8; margin-left:8px;">({remaining:.0f}s)</span>
        </div>"""
    
    return f"""
    <div style="padding:16px;">
        {banner}
        <p><strong>Volume:</strong> {db:.1f} dB
        <span style="color:{color};">{label}</span></p>
        <div style="background:#ddd; border-radius:8px; height:24px;">
            <div style="width:{pct:.1f}%; height:100%; background:{color};
            border-radius:8px; transition:width 0.15s;">
            </div>
        </div>
    </div>
    """


def process_audio(audio_data, state):
    if state is None:
        state = SessionState()
    if audio_data is None:
        return generate_gauge_html(0), state
    sample_rate, audio = audio_data
    db = compute_volume_db(audio)

    if db >= ALERT_DB:
        state.alert_until = time.time() + ALERT_DURATION
        state.alert_level = "red"
    elif db >= WARNING_DB:
        if state.alert_until - time.time() <= 0 or state.alert_level != "red":
            state.alert_until = time.time() + ALERT_DURATION
            state.alert_level = "yellow"

    return generate_gauge_html(db, state), state

with gr.Blocks(title="Sentinel") as app:
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
