import gradio as gr
import numpy as np

def process_audio(audio_data):
    if audio_data is None:
        return ""
    sample_rate, audio = audio_data
    return f"{sample_rate=}, {audio.shape=}, {audio.dtype=}"

with gr.Blocks() as app:
    gr.Markdown("#Microphone Input")
    audio_input = gr.Audio(sources="microphone", streaming=True, type="numpy")

    output = gr.Markdown("checking terminal...")

    audio_input.stream(
        fn=process_audio,
        inputs=[audio_input],
        outputs=[output],
    )

if __name__ == "__main__":
    app.launch()
