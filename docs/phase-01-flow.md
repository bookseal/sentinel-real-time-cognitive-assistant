# Phase 01: Sensory Foundation — Local Volume Guard

## Data Flow

```mermaid
graph TD
    A[Browser Microphone] -->|500ms chunks| B[Gradio Audio Stream]
    B --> C[Resample to 16kHz]
    C --> D[NumPy RMS Calculation]
    D --> E[Convert to dB Scale]
    E --> F{Volume Threshold Check}
    F -->|< 75 dB| G[Normal — Green UI]
    F -->|75-85 dB| H[Warning — Yellow UI]
    F -->|> 85 dB| I[RED ALERT — Red UI]

    D --> J[Sliding Window Buffer<br/>Last 5 chunks]
    J --> F

    C --> K[Silero VAD Filter]
    K -->|Speech Detected| L[Circular Audio Buffer<br/>30 chunks / ~15s]

    style I fill:#ff1744,color:#fff,stroke:#ff1744
    style H fill:#ffab00,color:#000,stroke:#ffab00
    style G fill:#00e676,color:#000,stroke:#00e676
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Local RMS via NumPy | $0.00 cost, <10ms latency vs ~$0.06/min cloud |
| dB SPL approximation | Human-readable scale (85 dB = shouting threshold) |
| 5-chunk sliding window | Prevents single-frame false positives |
| Zero network calls | All computation is local — no WebSocket or API usage |

## RMS Formula

$$X_{rms} = \sqrt{\frac{1}{n} \sum_{i=1}^{n} x_i^2}$$

Converted to dB: `dB_SPL ≈ 20 * log10(RMS) + 94`

## Files Modified

| File | Change |
|------|--------|
| `audio_logic.py` | New — `get_rms_db()`, `check_volume_threshold()` |
| `app.py` | Volume guard integration, Red Alert UI banner, dB meter |
