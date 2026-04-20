import gradio as gr
import numpy as np

def compute_volume_db(audio):
    """Convert raw audio samples to decibels (dB)."""
    if len(audio) == 0:
        return 0.0
    
    original_dtype = audio.dtype

    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    
    audio_f = audio.astype(np.float32)
    if np.issubdtype(original_dtype, np.integer):
        audio_f = audio_f / max(np.iinfo(audio.dtype).max, 1)

    rms = float(np.sqrt(np.mean(audio_f ** 2)))
    if rms < 1e-10:
        return 0.0
    db = 20 * np.log10(rms) + 94
    return max(db, 0.0)

def process_audio(audio_data):
    if audio_data is None:
        return "Waiting for audio..."
    sample_rate, audio = audio_data
    db = compute_volume_db(audio)
    return f"Volume: {db:.1f} dB"

with gr.Blocks() as app:
    gr.Markdown("# Sentinel - Volume Monitor")
    audio_input = gr.Audio(sources="microphone", streaming=True, type="numpy")
    output = gr.Markdown("Waiting for audio...")
    audio_input.stream(
        fn=process_audio,
        inputs=[audio_input],
        outputs=[output],
    )

if __name__ == "__main__":
    app.launch(share=True)
