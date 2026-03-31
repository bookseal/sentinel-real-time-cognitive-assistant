# =============================================================================
# app.py — Phase 00: Minimal Volume Gauge
#
# Data flow (this is the entire app):
#
#   [Browser Mic] --chunk every ~500ms--> [process_audio()]
#                                             |
#                                         compute_volume_db()
#                                             |
#                                         generate_gauge_html()
#                                             |
#                                  <--HTML gauge update-- [Browser]
# =============================================================================

import logging

import gradio as gr
import numpy as np

# =============================================================================
# Logging — Python's built-in way to print debug/info/error messages
# =============================================================================
# Why not just print()? logging gives you:
#   - Timestamps automatically
#   - Severity levels: DEBUG < INFO < WARNING < ERROR < CRITICAL
#   - Easy to turn on/off by level (e.g. show only ERROR in production)
#
# Usage:
#   logger.info("server started")      → 2026-03-31 11:00:00 [INFO] sentinel: server started
#   logger.error("something broke")    → 2026-03-31 11:00:00 [ERROR] sentinel: something broke
#   logger.debug("x = 42")            → (hidden by default, level=DEBUG to show)

logging.basicConfig(
    level=logging.INFO,                                     # show INFO and above (hide DEBUG)
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",  # output format template
)
logger = logging.getLogger("sentinel")   # create a logger named "sentinel"


# =============================================================================
# Constants
# =============================================================================
WARNING_DB = 60.0    # yellow threshold — elevated voice
ALERT_DB = 70.0      # red threshold — shouting


# =============================================================================
# Audio Analysis
# =============================================================================

# Python type hints:
#   def foo(x: int) -> str:
#       ^^^^^^^^      ^^^^
#       parameter      return type
#       type hint      hint
#
# These are just LABELS for humans and editors (IDE autocomplete, error checking).
# Python does NOT enforce them at runtime. You could return an int and Python won't complain.
# But your IDE will show a warning, which helps catch bugs early.

def compute_volume_db(audio: np.ndarray) -> float:
    """Convert raw audio samples to decibels (dB).

    Steps:
      1. Normalize: int samples (e.g. -32768~32767) → float (-1.0~1.0)
      2. RMS: Root Mean Square — average loudness of the chunk
      3. dB: 20 * log10(rms) + 94  →  human-readable loudness scale
    """
    if len(audio) == 0:
        return 0.0

    # Step 1 — normalize integer audio to float range [-1.0, 1.0]
    audio_f = audio.astype(np.float32)
    if np.issubdtype(audio.dtype, np.integer):
        audio_f = audio_f / max(np.iinfo(audio.dtype).max, 1)

    # Step 2 — RMS (Root Mean Square): sqrt(mean(samples²))
    #   silence → 0.0,  normal talk → ~0.01,  shouting → ~0.1
    rms = float(np.sqrt(np.mean(audio_f ** 2)))
    if rms < 1e-10:
        return 0.0

    # Step 3 — convert to dB (logarithmic, matches how humans hear)
    #   +94 offset: in acoustics, digital 0 dBFS ≈ 94 dB SPL
    db = 20 * np.log10(rms) + 94
    return max(db, 0.0)


# =============================================================================
# HTML Gauge — the visual output sent to the browser
# =============================================================================
def generate_gauge_html(db: float) -> str:
    """Return an HTML string with a colored volume bar.

    Color: green (quiet) → yellow (moderate) → red (loud)
    """
    if db >= ALERT_DB:
        color, label = "red", "LOUD"
    elif db >= WARNING_DB:
        color, label = "orange", "MODERATE"
    else:
        color, label = "green", "QUIET"

    # Map dB [30~100] → bar width [0%~100%]
    pct = min(max((db - 30) / 70 * 100, 0), 100)

    return f"""
    <div style="padding:16px;">
        <p><strong>Volume:</strong> {db:.1f} dB — <span style="color:{color};">{label}</span></p>
        <div style="background:#ddd; border-radius:8px; height:24px;">
            <div style="width:{pct:.1f}%; height:100%; background:{color};
                        border-radius:8px; transition:width 0.15s;">
            </div>
        </div>
    </div>
    """


# =============================================================================
# Audio Processing — Gradio calls this on every mic chunk (~500ms)
# =============================================================================
def process_audio(audio_data):
    """Receive a streaming audio chunk, return updated gauge HTML.

    Gradio sends audio_data as a tuple:
      (sample_rate, audio_array)
       e.g. (48000, np.array([0, 12, -34, ...]))
    """
    if audio_data is None:
        return generate_gauge_html(0)

    sample_rate, audio = audio_data

    # Stereo → Mono (average left + right channels)
    if audio.ndim > 1:
        audio = audio.mean(axis=1).astype(audio.dtype)

    db = compute_volume_db(audio)
    return generate_gauge_html(db)


# =============================================================================
# Gradio UI — build the web page
# =============================================================================
def build_app() -> gr.Blocks:
    # gr.Blocks = a container for laying out Gradio components
    # (like a blank HTML page you fill with widgets)

    # ---- "with" keyword — Context Manager (for C programmers) ----------------
    #
    # In C you do:          In Python "with" does it automatically:
    #
    #   FILE *f = fopen();     with open("file") as f:
    #   // use f                   # use f
    #   fclose(f);                 # fclose() called automatically on exit
    #
    # "with X as Y" means:
    #   1. Call X.__enter__()  → returns Y  (like init/open/acquire)
    #   2. Run the indented block
    #   3. Call X.__exit__()   → always runs (like cleanup/close/release)
    #                            even if an exception is thrown (like finally{})
    #
    # Here, gr.Blocks().__enter__() sets a global context so that any
    # Gradio component created inside the block (gr.Audio, gr.HTML, ...)
    # is automatically registered as a child of this Blocks container.
    # On __exit__(), the layout is finalized.
    #
    # C analogy:
    #   gr_blocks *app = gr_blocks_begin("Sentinel");  // __enter__
    #   gr_add_audio(app, ...);
    #   gr_add_html(app, ...);
    #   gr_blocks_end(app);                            // __exit__
    # --------------------------------------------------------------------------

    with gr.Blocks(title="Sentinel — Volume Gauge") as app:

        gr.Markdown("# Sentinel\nPhase 00 — Volume Gauge")

        # Microphone input — streams audio chunks in real-time
        audio_input = gr.Audio(
            sources=["microphone"],
            streaming=True,        # real-time streaming (not "record then submit")
            label="Tap to Record",
            type="numpy",          # return format: (sample_rate, np.ndarray)
        )

        # Volume gauge — plain HTML, updated on every chunk
        gauge = gr.HTML(value=generate_gauge_html(0))

        # Wiring: connect audio stream → processing function → gauge output
        # Every ~500ms: audio_input produces a chunk
        #   → process_audio(chunk) runs
        #   → return value replaces gauge HTML
        audio_input.stream(
            fn=process_audio,
            inputs=[audio_input],
            outputs=[gauge],
        )

    return app


# =============================================================================
# Entry Point
# =============================================================================
# __name__ == "__main__" means: "only run this when executing the file directly"
#   python app.py        → __name__ is "__main__" → runs
#   import app           → __name__ is "app"      → skipped (just imports functions)

if __name__ == "__main__":
    logger.info("Starting Sentinel Phase 00 — Minimal Volume Gauge")
    app = build_app()
    app.launch(
        server_name="0.0.0.0",   # listen on all interfaces (required in Docker)
        server_port=7860,         # port number (matches Dockerfile EXPOSE)
        show_error=True,          # show Python errors in browser (helpful for dev)
    )
