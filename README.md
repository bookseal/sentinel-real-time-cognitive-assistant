# 🛡️ Sentinel: Real-time Cognitive Assistant

[![Live Demo](https://img.shields.io/badge/Live-sentinel.bit--habit.com-ff1744?style=for-the-badge&logo=kubernetes&logoColor=white)](https://sentinel.bit-habit.com)
[![K3s](https://img.shields.io/badge/K3s-Oracle_OCI-326ce5?style=flat-square&logo=kubernetes)](https://sentinel.bit-habit.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python)](https://python.org)
[![Gradio](https://img.shields.io/badge/Gradio-4.0+-f97316?style=flat-square)](https://gradio.app)

> **"Converting conversational noise into verified signal through emotional and factual surveillance."**

Sentinel is a real-time meeting intelligence system that monitors vocal arousal, detects factual claims, verifies them against the web, and intervenes when conflict escalates — all while minimizing cloud API costs through local-first computation.

---

## Live Deployment

**🌐 https://sentinel.bit-habit.com**

Sentinel runs as a containerized microservice on **K3s (Oracle OCI)**, exposed via Traefik Ingress with automatic TLS. Connect your microphone and the system begins analyzing in real-time.

```
Browser → K3s Ingress (Traefik + TLS) → Sentinel Pod (port 7860) → Gradio UI
```

---

## Architecture Overview

```mermaid
graph TD
    A[🎤 Browser Microphone] -->|500ms chunks| B[Gradio Streaming UI]
    B --> C[Resample 16kHz]
    C --> D{Silero VAD}
    C --> E[🔊 Volume Guard<br/>Phase 01]

    D -->|Speech| F[Circular Buffer<br/>30 chunks / 15s]
    D -->|Silence| G[Dropped — $0]
    F --> H[WebSocket Client]
    H --> I[☁️ OpenAI Realtime API<br/>or 🏠 Local vLLM]

    I --> J[📝 Transcript + Emotion Score]
    J --> K[🎭 Speaker Diarization<br/>Phase 03]
    J --> L[🔍 Claim Detection<br/>Phase 04]
    L --> M[✅ Fact-Check Oracle<br/>Phase 05]
    J --> N[📋 Action Items<br/>Phase 06]

    C --> O[📷 Webcam Capture<br/>Phase 07]
    O --> P[Mediapipe Face Mesh]

    E --> Q[Sentinel Index<br/>Si = 0.6×Audio + 0.4×Vision]
    P --> Q
    J --> Q

    Q --> R{Si > 0.8?}
    R -->|Yes| S[🔔 Slack/Zoom Alert<br/>Phase 09]
    R -->|Si > 0.9 for 10s| T[🕊️ Verbal Mediation<br/>Phase 10]

    style E fill:#ff1744,color:#fff
    style G fill:#333,color:#888
    style Q fill:#ffab00,color:#000
    style T fill:#4fc3f7,color:#000
```

---

## The 10 Phases

Sentinel is built in 10 incremental phases, each on its own feature branch. The philosophy: **local computation first, cloud only when necessary**.

### Phase 01 — 🔊 Local Volume Guard
> **Branch**: `feature/phase-01-volume-guard`

Detects shouting using NumPy RMS → dB conversion. Zero cloud calls, zero cost, sub-10ms latency.

```mermaid
graph LR
    A[🎤 Audio Chunk] --> B[NumPy RMS]
    B --> C[dB Conversion<br/>20×log₁₀ + 94]
    C --> D[Sliding Window<br/>5 chunks]
    D --> E{"Threshold?"}
    E -->|"< 75 dB"| F[🟢 Normal]
    E -->|"75–85 dB"| G[🟡 Warning]
    E -->|"> 85 dB"| H[🔴 RED ALERT]

    style A fill:#424242,color:#fff
    style B fill:#ff8a80,color:#000
    style C fill:#ff5252,color:#fff
    style D fill:#ff1744,color:#fff
    style F fill:#00e676,color:#000
    style G fill:#ffab00,color:#000
    style H fill:#ff1744,color:#fff,stroke:#ff0000,stroke-width:3px
```

| Key | Value |
|-----|-------|
| Shout Threshold | 85 dB SPL |
| Sliding Window | 5 chunks (2.5s) |
| Cost | **$0.00** |
| Core File | [`audio_logic.py`](audio_logic.py) |

> 📖 **[Full Engineering Guide →](docs/phase-01-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

### Phase 02 — 🧠 VAD-Gated Emotion Guard
> **Branch**: `feature/phase-02-emotion-guard`

Silero VAD gates the OpenAI API — only speech gets sent, silence costs $0. Includes a 1-second grace period to prevent cutting off mid-sentence.

```mermaid
graph LR
    A[🎤 Audio Chunk] --> B[Silero VAD]
    B --> C{"P(speech) > 0.5?"}
    C -->|Yes| D[🟢 Gate OPEN]
    C -->|No| E{"Grace Period?"}
    E -->|Remaining| D
    E -->|Expired| F[🔴 Gate CLOSED<br/>$0.00]
    D --> G[WebSocket Send]
    G --> H[☁️ OpenAI Realtime API]
    H --> I[🧠 Emotion Score<br/>0.0 — 1.0]

    style B fill:#00e676,color:#000
    style D fill:#00e676,color:#000,stroke:#00c853,stroke-width:2px
    style F fill:#616161,color:#fff
    style H fill:#42a5f5,color:#fff
    style I fill:#69f0ae,color:#000
```

| Key | Value |
|-----|-------|
| VAD Threshold | P(speech) > 0.5 |
| Grace Period | 2 chunks (~1s) |
| Emotion Output | Arousal 0.0–1.0 via `report_emotion` tool |
| Core Files | [`vad.py`](vad.py), [`ws_client.py`](ws_client.py) |

> 📖 **[Full Engineering Guide →](docs/phase-02-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

### Phase 03 — 🎭 Speaker Diarization
> **Branch**: `feature/phase-03-diarization`

Identifies **who** is speaking and renders color-coded chat bubbles. Users can assign custom names via the Speaker Legend panel.

```mermaid
graph LR
    A[☁️ OpenAI API] --> B["report_emotion()<br/>+ speaker_id"]
    B --> C[Speaker State<br/>Manager]
    C --> D["🔵 Speaker 0"]
    C --> E["🟢 Speaker 1"]
    C --> F["🟠 Speaker 2"]
    D & E & F --> G[Color-coded<br/>Chat Bubbles]
    G --> H[📝 Transcript UI]

    style D fill:#4fc3f7,color:#000
    style E fill:#81c784,color:#000
    style F fill:#ffb74d,color:#000
    style C fill:#e1f5fe,color:#000
    style H fill:#263238,color:#fff
```

| Key | Value |
|-----|-------|
| Speaker Colors | 5 distinct colors (blue, green, orange, pink, purple) |
| Name Assignment | Manual via UI (e.g., `speaker_0` → "Gichan") |
| Core File | [`app.py`](app.py) — `SPEAKER_COLORS`, `update_speaker_name()` |

> 📖 **[Full Engineering Guide →](docs/phase-03-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

### Phase 04 — 🔍 Claim Detection (LangGraph)
> **Branch**: `feature/phase-04-claim-detection`

Filters conversation to find **checkable facts** using regex pattern matching — no LLM needed. Only high-confidence claims (≥0.6) trigger highlighting.

```mermaid
graph LR
    A[📝 Transcript<br/>Chunk] --> B[Buffer<br/>30 chunks]
    B --> C{"Small Talk?"}
    C -->|"Hello, Hi..."| D[⬛ Skip]
    C -->|No| E[Pattern Scan<br/>6 categories]
    E --> F["Score =<br/>0.5 + N × 0.15"]
    F --> G{">= 0.6?"}
    G -->|Yes| H[⚡ Highlight<br/>Yellow]
    G -->|No| I[Normal UI]
    H --> J[Queue for<br/>Fact-Check]

    style D fill:#616161,color:#aaa
    style E fill:#fff176,color:#000
    style F fill:#ffab00,color:#000
    style H fill:#ffab00,color:#000,stroke:#ff8f00,stroke-width:3px
    style J fill:#7c4dff,color:#fff
```

| Key | Value |
|-----|-------|
| Pattern Categories | 6 (numbers, dates, statistics, absolutes, named entities, factual assertions) |
| Confidence Formula | `0.5 + matched_patterns × 0.15` |
| False Positive Guard | 4 small-talk rejection patterns |
| Core File | [`agent/claim_detector.py`](agent/claim_detector.py) |

> 📖 **[Full Engineering Guide →](docs/phase-04-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

### Phase 05 — ✅ Fact-Check Oracle (Tavily)
> **Branch**: `feature/phase-05-fact-check`

Detected claims are verified against the web using **Tavily AI Search** + **GPT-4o-mini** as a judge. Returns: Verified, False, or Disputed.

```mermaid
sequenceDiagram
    participant C as ⚡ Claim
    participant T as 🔎 Tavily Search
    participant J as 🧠 GPT-4o-mini Judge
    participant U as 🖥️ UI

    C->>T: "Is it true that: [claim]"
    T-->>J: Top 3 sources + AI answer
    J->>J: Compare claim vs evidence
    J-->>U: ✅ Verified
    Note over J,U: or ❌ False / ⚠️ Disputed

    rect rgb(124, 77, 255, 0.1)
        Note over T,J: RAG Pipeline<br/>(Retrieval → Augment → Generate)
    end
```

| Key | Value |
|-----|-------|
| Search Engine | Tavily (LLM-ready content) |
| Judge Model | GPT-4o-mini ($0.15/1M tokens) |
| Target SLA | < 5 seconds |
| Core Files | [`tools/search.py`](tools/search.py), [`agent/verifier.py`](agent/verifier.py) |

> 📖 **[Full Engineering Guide →](docs/phase-05-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

### Phase 06 — 📋 Action Item Extraction
> **Branch**: `feature/phase-06-action-items`

Automatically extracts commitments ("I will send the report by Friday") from live conversation. Exports as downloadable `.md` file.

```mermaid
graph LR
    A[📝 Live<br/>Transcript] --> B[Sliding Window<br/>20 chunks]
    B --> C{"Vague?<br/>maybe, later..."}
    C -->|Yes| D[🚫 Rejected]
    C -->|No| E{"Commitment?<br/>I will, we need..."}
    E -->|Yes| F[🤖 LLM Extract<br/>or Regex Fallback]
    E -->|No| G[Skip]
    F --> H[Dedup Check]
    H --> I[📋 Task List]
    I --> J[📥 Download .md]

    style D fill:#616161,color:#aaa
    style F fill:#26c6da,color:#000
    style I fill:#00bcd4,color:#000,stroke:#0097a7,stroke-width:2px
    style J fill:#80deea,color:#000
```

| Key | Value |
|-----|-------|
| Commitment Patterns | 8 regex patterns |
| Vague Rejection | "I'll do it later" → filtered out |
| Export | Markdown table with Task, Owner, Deadline |
| Core File | [`agent/summarizer.py`](agent/summarizer.py) |

> 📖 **[Full Engineering Guide →](docs/phase-06-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

### Phase 07 — 📷 Multi-modal Vision Guard
> **Branch**: `feature/phase-07-vision`

Webcam detects facial stress (brow furrow, jaw clench, eye squint) using **Mediapipe Face Mesh** — 100% local, no frames sent externally. Fused with audio into the **Sentinel Index**.

```mermaid
graph TD
    A[🎤 Microphone] --> B[Audio Arousal<br/>0.0 — 1.0]
    C[📷 Webcam] --> D[Mediapipe<br/>Face Mesh]
    D --> E["😠 Brow Furrow (0.4)"]
    D --> F["😬 Jaw Clench (0.35)"]
    D --> G["👀 Eye Squint (0.25)"]
    E & F & G --> H[Visual Stress<br/>0.0 — 1.0]
    B -->|"× 0.6"| I[⚖️ Sentinel Index]
    H -->|"× 0.4"| I
    I --> J["Si = 0.6×Audio + 0.4×Vision"]

    style B fill:#f06292,color:#fff
    style H fill:#f06292,color:#fff
    style I fill:#ffab00,color:#000,stroke:#ff8f00,stroke-width:3px
    style J fill:#ff6f00,color:#fff
    style D fill:#e1bee7,color:#000
```

| Key | Value |
|-----|-------|
| Landmarks | 468 (Mediapipe Face Mesh) |
| Stress Formula | `0.4×brow + 0.35×jaw + 0.25×eye` |
| Sentinel Index | `Si = 0.6×Audio + 0.4×Vision` |
| Core File | [`vision/face_monitor.py`](vision/face_monitor.py) |

> 📖 **[Full Engineering Guide →](docs/phase-07-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

### Phase 08 — 🏠 Edge AI ($0 Token Migration)
> **Branch**: `feature/phase-08-edge-ai`

Switch from OpenAI cloud to local **vLLM** (Llama-3 8B) or **Ollama** with one environment variable. Same WebSocket interface, zero variable cost.

```mermaid
graph TD
    A["🔧 LLM_PROVIDER"] --> B{"Value?"}
    B -->|"openai"| C["☁️ OpenAI API<br/>wss://api.openai.com<br/>💰 $50–200/mo"]
    B -->|"local"| D["🏠 Local vLLM<br/>ws://localhost:8000<br/>💚 $0/mo"]
    C --> E[Same WebSocket<br/>Interface]
    D --> E
    E --> F[Sentinel App]

    style C fill:#ef5350,color:#fff
    style D fill:#66bb6a,color:#000,stroke:#43a047,stroke-width:3px
    style E fill:#e8f5e9,color:#000
    style A fill:#fff9c4,color:#000
```

| Key | Value |
|-----|-------|
| Switch | `LLM_PROVIDER=local` |
| Local Model | Meta-Llama-3-8B-Instruct |
| GPU Requirement | 1× NVIDIA (8–16 GB VRAM) |
| Core Files | [`k8s/vllm-deployment.yaml`](k8s/vllm-deployment.yaml), [`ws_client.py`](ws_client.py) |

> 📖 **[Full Engineering Guide →](docs/phase-08-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

### Phase 09 — 🔔 Ecosystem Integration (Slack/Zoom)
> **Branch**: `feature/phase-09-integration`

When the Sentinel Index exceeds threshold, alerts fire to **Slack** and **Zoom** automatically. 5-minute cool-down prevents spam.

```mermaid
graph LR
    A["⚖️ Sentinel Index"] --> B{"Si ≥ 0.8?"}
    B -->|No| C[No Action]
    B -->|"≥ 0.8"| D[🟡 RED ALERT]
    B -->|"≥ 0.9"| E[🔴 CRITICAL]
    D & E --> F{"Cool-down<br/>5 min?"}
    F -->|Active| G[⏳ Suppressed]
    F -->|Clear| H[Alert Dispatcher]
    H --> I[💬 Slack<br/>Webhook]
    H --> J[📹 Zoom<br/>Chat API]

    style D fill:#ef5350,color:#fff
    style E fill:#b71c1c,color:#fff,stroke:#f44336,stroke-width:3px
    style G fill:#616161,color:#aaa
    style I fill:#42a5f5,color:#fff
    style J fill:#42a5f5,color:#fff
    style C fill:#424242,color:#888
```

| Key | Value |
|-----|-------|
| Channels | Slack Incoming Webhook, Zoom Chat API |
| Red Alert Threshold | Si ≥ 0.8 |
| Critical Threshold | Si ≥ 0.9 |
| Cool-down | 300 seconds (5 min) |
| Core File | [`integration/dispatcher.py`](integration/dispatcher.py) |

> 📖 **[Full Engineering Guide →](docs/phase-09-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

### Phase 10 — 🕊️ Autonomous Verbal Mediation
> **Branch**: `feature/phase-10-mediation`

When conflict escalates beyond 0.9 for 10+ seconds, Sentinel generates a calming de-escalation message via **OpenAI TTS** and plays it to the meeting. Users have a "Silence Sentinel" override button.

```mermaid
stateDiagram-v2
    [*] --> Monitoring
    Monitoring --> Escalating: Si > 0.9
    Escalating --> Monitoring: Si drops below 0.9
    Escalating --> Mediating: Sustained > 10s
    Mediating --> GenerateScript: LLM or fallback
    GenerateScript --> TTSAudio: OpenAI TTS (nova)
    TTSAudio --> Cooldown: Play calming message
    Cooldown --> Monitoring: 120s elapsed

    Monitoring --> Silenced: 🔇 User clicks Silence
    Silenced --> Monitoring: 🔊 User clicks Enable

    state Mediating {
        direction LR
        [*] --> CheckCooldown
        CheckCooldown --> Generate: Clear
        CheckCooldown --> Skip: Active
    }
```

| Key | Value |
|-----|-------|
| Trigger | Si > 0.9 sustained for 10s |
| TTS Voice | `nova` (calm, authoritative) at 0.9× speed |
| Cool-down | 120 seconds between interventions |
| Safety | "Silence Sentinel" button (user override) |
| Core File | [`agent/mediator.py`](agent/mediator.py) |

> 📖 **[Full Engineering Guide →](docs/phase-10-flow.md)** — 3-chapter deep dive (1-min / 10-min / 100-min)

---

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Gradio 4.0+ | Real-time streaming UI with audio input |
| **Audio AI** | Silero VAD v5 | Local voice activity detection (CPU) |
| **Speech** | OpenAI Realtime API | Transcription + emotion analysis |
| **Vision** | Mediapipe Face Mesh | Local facial stress detection |
| **Search** | Tavily AI Search | LLM-ready web search for fact-checking |
| **Agent** | LangGraph (concept) | Stateful claim detection pipeline |
| **LLM** | GPT-4o-mini / Llama-3 8B | Judge node, action extraction, mediation scripts |
| **TTS** | OpenAI TTS (nova) | Verbal de-escalation audio |
| **Infra** | K3s on Oracle OCI | Production Kubernetes cluster |
| **Ingress** | Traefik + TLS | HTTPS routing at `sentinel.bit-habit.com` |
| **Alerts** | Slack / Zoom Webhooks | External notification channels |

---

## Quick Start

```bash
# 1. Clone
git clone git@github.com:bookseal/sentinel-real-time-cognitive-assistant.git
cd sentinel-real-time-cognitive-assistant

# 2. Configure
echo "OPENAI_API_KEY=sk-..." > .env

# 3. Run
docker-compose up -d --build
docker compose logs -f    # Find the gradio.live link

# 4. Open browser → allow microphone → start speaking
```

---

## Project Structure

```
sentinel-real-time-cognitive-assistant/
├── app.py                    # Main Gradio UI + audio processing pipeline
├── audio_logic.py            # Phase 01: RMS dB calculation, volume thresholds
├── audio_buffer.py           # Thread-safe circular buffer (30 chunks)
├── vad.py                    # Silero VAD wrapper with grace period
├── ws_client.py              # OpenAI Realtime API WebSocket client
├── agent/
│   ├── claim_detector.py     # Phase 04: Regex-based claim classification
│   ├── verifier.py           # Phase 05: Tavily + GPT-4o-mini fact-check
│   ├── summarizer.py         # Phase 06: Action item extraction
│   └── mediator.py           # Phase 10: TTS verbal mediation
├── tools/
│   └── search.py             # Phase 05: Tavily AI Search wrapper
├── vision/
│   └── face_monitor.py       # Phase 07: Mediapipe facial stress detection
├── integration/
│   └── dispatcher.py         # Phase 09: Slack/Zoom alert dispatcher
├── k8s/
│   ├── deployment.yaml       # Pod spec with health probes
│   ├── service.yaml          # ClusterIP (port 80 → 7860)
│   ├── ingress.yaml          # Traefik ingress for sentinel.bit-habit.com
│   ├── vllm-deployment.yaml  # Phase 08: Local vLLM/Ollama deployment
│   └── secret.yaml.example   # Template (real secret is .gitignored)
├── docs/
│   ├── PLAN.md               # Full 10-phase execution blueprint
│   └── phase-XX-flow.md      # Per-phase 3-chapter engineering guides
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Git Workflow

| Branch | Purpose |
|--------|---------|
| `main` | Production — mirrors K3s deployment |
| `develop` | Integration staging |
| `feature/phase-XX-*` | Phase implementation branches |

**Commit format**: [Conventional Commits](https://www.conventionalcommits.org/) — `type(scope): description`

---

## Development Philosophy

> *"Cost is a technical debt. Minimize token burn through local logic."*

1. **Local First**: Compute locally (NumPy, Silero, Mediapipe) before calling any cloud API
2. **Frugal Architecture**: VAD-gate every API call — never send silence to OpenAI
3. **Progressive Enhancement**: Each phase adds capability without breaking previous layers
4. **Graceful Degradation**: Missing API keys? The system falls back to local-only mode

---

© 2026 Gichan Lee. Built on 42 Seoul Foundations. Deployed via K3s on Oracle OCI. Served by Traefik.
