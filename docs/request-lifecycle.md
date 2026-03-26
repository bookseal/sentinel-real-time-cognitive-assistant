# Request Lifecycle: From Browser to HTML

> Traces every file involved when a user hits `sentinel.bit-habit.com` —
> from DNS resolution through Kubernetes networking to the final HTML
> rendered in the browser.

---

## Stage 1: Network Ingress (Kubernetes)

When the browser sends `GET https://sentinel.bit-habit.com/`, the request
enters the Kubernetes cluster and passes through three resources in order.

### 1-1. `k8s/ingress.yaml` — Domain Routing & TLS Termination

```
Browser ──HTTPS──▶ Traefik Ingress Controller
```

| Field | Value | Purpose |
|-------|-------|---------|
| `host` | `sentinel.bit-habit.com` | Match incoming domain |
| `secretName` | `tls-secret` | TLS certificate for HTTPS termination |
| `backend.service.name` | `sentinel-svc` | Forward decrypted traffic to this Service |
| `backend.service.port` | `80` | Target port on the Service |

Traefik terminates TLS here — downstream traffic within the cluster is
plain HTTP.

### 1-2. `k8s/service.yaml` — Port Mapping

```
Traefik ──HTTP :80──▶ Service ──:7860──▶ Pod
```

| Field | Value | Purpose |
|-------|-------|---------|
| `selector.app` | `sentinel` | Find Pods labeled `app: sentinel` |
| `port` | `80` | Port the Service listens on (from Ingress) |
| `targetPort` | `7860` | Port on the Pod to forward to |

The Service is a stable network endpoint. Even if the Pod restarts and
gets a new IP, the Service name `sentinel-svc` stays the same.

### 1-3. `k8s/deployment.yaml` — Pod Specification

```
Service ──:7860──▶ Container (python app.py)
```

| Field | Value | Purpose |
|-------|-------|---------|
| `image` | `sentinel:latest` | Docker image to run |
| `containerPort` | `7860` | Port the app listens on inside the container |
| `envFrom.secretRef` | `sentinel-secret` | Inject env vars (API keys, etc.) |

**Key point:** There is no `command:` field in this Deployment. When
Kubernetes omits `command`, it falls back to the Docker image's `CMD`
instruction. That brings us to Stage 2.

---

## Stage 2: Container Image (Built Once)

These files define the runtime environment. They are not hit on every
request — they are baked into the Docker image at build time.

### 2-1. `Dockerfile` — Image Build Recipe

```dockerfile
FROM python:3.10-slim
# ...
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-download Silero VAD model
RUN python -c "import torch; torch.hub.load(...)"
COPY . .
CMD ["python", "app.py"]    # ← This is what the Pod runs
```

The `CMD` on the last line is the default entrypoint. Since
`deployment.yaml` has no `command:` override, Kubernetes executes
`python app.py` when the Pod starts.

### 2-2. `requirements.txt` — Python Dependencies

Installed at image build time via `pip install`. Contains:
- `gradio` — Web UI framework (serves HTTP + WebSocket)
- `numpy` — Audio math (RMS, FFT)
- `torch` — Required by Silero VAD model

### 2-3. `.env` — Environment Variables (Local Dev Only)

Used by `docker-compose.yml` during local development. In production
(K8s), environment variables come from `sentinel-secret` instead.

---

## Stage 3: Application Startup & HTTP Response

Once the Pod is running, `python app.py` starts a Gradio server on port
7860. This is where the actual HTTP request is handled.

### 3-1. `app.py` — The Entrypoint (Hub of Everything)

When `app.py` starts, it executes:

```python
# Line 386-393
if __name__ == "__main__":
    app = build_app()       # Build the Gradio UI
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,   # ← The port K8s Service forwards to
    )
```

**On `GET /`**, Gradio renders the UI defined in `build_app()` (line 316)
into a full HTML page and returns it. The function does:

1. Injects **custom CSS** — Inter font, dark gradient background, hidden footer
2. Adds **`gr.HTML()`** — the "Sentinel" header with gradient text
3. Adds **`gr.Audio()`** — microphone streaming input widget
4. Calls **`generate_status_html()`** — the initial dashboard (gauges at zero)
5. Adds **`gr.Slider()`** — sensitivity control (0.5–2.0)
6. Adds **`gr.Button()`** — reset button
7. Wires **event handlers** — `audio_input.stream()` → `process_audio_chunk()`

### 3-2. `app.py:168` `generate_status_html()` — Dashboard HTML

This function builds the inline HTML for the dashboard panel:
- Volume gauge bar (green/yellow/red based on dB)
- Pitch gauge bar (green/yellow/red based on Hz)
- VAD status dot (speech detected or silence)
- Alert banner (persistent for 5 seconds when triggered)

On the **initial page load**, all values are zero — the gauges are empty
and no alert is shown. This HTML is embedded inside Gradio's full-page
HTML shell and sent to the browser.

**This is where the initial HTML response is complete.** The browser now
has everything it needs to render the page.

---

## Stage 4: Real-Time Streaming (After Page Load)

After the page loads, the user grants microphone permission. Audio chunks
(~500ms each) flow via WebSocket back to the server. Each chunk triggers
the following file chain:

### 4-1. `app.py:87` `process_audio_chunk()` — Audio Pipeline Entry

Receives `(sample_rate, np.ndarray)` from Gradio's streaming audio
widget. Resamples to 16kHz if needed, then calls into three modules:

### 4-2. `audio_logic.py` — Volume & Pitch Math

| Function | Purpose |
|----------|---------|
| `get_rms_db(audio)` | RMS → dB SPL conversion (the core volume metric) |
| `get_pitch_hz(audio, sr)` | FFT peak detection in 85–400 Hz voice range |
| `check_volume_threshold(history, db)` | Sliding-window (5 chunks) alert classification |

All computation is pure NumPy — zero network calls, < 10ms latency.

### 4-3. `vad.py` — Voice Activity Detection

`VoiceActivityDetector` wraps the Silero VAD model (PyTorch). Determines
whether the audio chunk contains human speech. Only speech chunks proceed
to the buffer.

### 4-4. `audio_buffer.py` — Circular Audio Buffer

`CircularAudioBuffer` stores up to 30 chunks (~15 seconds) of speech
audio in a thread-safe `deque`. Used for potential downstream processing
(future phases).

### 4-5. `app.py:168` `generate_status_html()` — Updated Dashboard

After all analysis is done, `generate_status_html()` is called again
with updated `app_state` values. The new HTML is pushed to the browser
via Gradio's WebSocket connection, replacing the dashboard in real-time.

---

## Visual Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  BROWSER: https://sentinel.bit-habit.com                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS GET /
                           ▼
┌──────────────────────────────────────────────────┐
│  k8s/ingress.yaml                                │
│  Traefik: TLS termination, route to sentinel-svc │
└──────────────────────────┬───────────────────────┘
                           │ HTTP :80
                           ▼
┌──────────────────────────────────────────────────┐
│  k8s/service.yaml                                │
│  sentinel-svc: port 80 → targetPort 7860         │
└──────────────────────────┬───────────────────────┘
                           │ :7860
                           ▼
┌──────────────────────────────────────────────────┐
│  k8s/deployment.yaml                             │
│  Pod running sentinel:latest                     │
│  (no command: override → uses Dockerfile CMD)    │
└──────────────────────────┬───────────────────────┘
                           │ python app.py
                           ▼
┌──────────────────────────────────────────────────┐
│  app.py                                          │
│  build_app() → Gradio Blocks UI                  │
│  generate_status_html() → initial dashboard      │
│  ← Returns full HTML page to browser             │
└──────────────────────────┬───────────────────────┘
                           │ WebSocket (after mic enabled)
                           ▼
┌──────────────────────────────────────────────────┐
│  app.py: process_audio_chunk()                   │
│    ├── audio_logic.py  (volume dB, pitch Hz)     │
│    ├── vad.py          (speech detection)         │
│    ├── audio_buffer.py (speech chunk storage)     │
│    └── generate_status_html() → updated HTML      │
│       ← Pushed to browser via WebSocket           │
└──────────────────────────────────────────────────┘
```

## File Reading Order (Recommended)

For someone reading the code for the first time:

| Order | File | Why |
|-------|------|-----|
| 1 | `k8s/ingress.yaml` | Understand how the domain maps to the cluster |
| 2 | `k8s/service.yaml` | Understand port forwarding |
| 3 | `k8s/deployment.yaml` | Understand what runs in the Pod |
| 4 | `Dockerfile` | Understand the runtime environment and default CMD |
| 5 | `app.py` | **The hub** — UI definition + audio processing pipeline |
| 6 | `audio_logic.py` | Volume/pitch math (pure NumPy) |
| 7 | `vad.py` | Voice activity detection (Silero model) |
| 8 | `audio_buffer.py` | Simplest file — circular buffer for audio chunks |
