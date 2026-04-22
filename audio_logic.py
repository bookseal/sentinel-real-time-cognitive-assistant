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
        audio_f = audio_f / max(np.iinfo(original_dtype).max, 1)

    rms = float(np.sqrt(np.mean(audio_f ** 2)))
    if rms < 1e-10:
        return 0.0
    db = 20 * np.log10(rms) + 94
    return max(db, 0.0)


