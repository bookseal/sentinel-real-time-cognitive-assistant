# Sentinel: Real-time Cognitive Assistant

[![Live](https://img.shields.io/badge/Live-sentinel.bit--habit.com-ff1744?style=for-the-badge&logo=kubernetes&logoColor=white)](https://sentinel.bit-habit.com)
[![K3s](https://img.shields.io/badge/K3s-Oracle_OCI-326ce5?style=flat-square&logo=kubernetes)](https://sentinel.bit-habit.com)
[![Python](https://img.shields.io/badge/Python-3.10-3776ab?style=flat-square&logo=python)](https://python.org)
[![Gradio](https://img.shields.io/badge/Gradio-4.0+-f97316?style=flat-square)](https://gradio.app)

A real-time meeting voice monitor that detects vocal escalation and alerts participants before conversations get out of hand. Built with local-first computation — no cloud API needed for core detection.

**Live at https://sentinel.bit-habit.com**

---

## Current State: v0.0.x (Volume Gauge)

Streams browser microphone audio, computes volume in real-time, and displays a color-coded gauge with persistent alerts.

```
Browser Mic → Gradio Streaming → NumPy RMS → dB Gauge + Alert Banner
```

**Features:**
- Real-time volume (dB) gauge: green / yellow / red
- 10-second persistent alert banner when voice is raised
- Zero cloud API calls — all computation is local

**Stack:** `gradio` + `numpy` on K3s (Oracle OCI)

> Full build/deploy guide: **[docs/phase-00-guide.md](docs/phase-00-guide.md)**

---

## Roadmap

Sentinel is built incrementally. Each version adds a layer of intelligence.

| Version | Milestone | Status |
|---------|-----------|--------|
| **v0.0** | Volume gauge + persistent alert | **Deployed** |
| v0.1 | VAD-gated emotion detection (Silero + OpenAI Realtime API) | Planned |
| v0.2 | Speaker diarization + color-coded transcript | Planned |
| v0.3 | Claim detection + fact-checking (Tavily) | Planned |
| v0.4 | Multi-modal vision guard (Mediapipe Face Mesh) | Planned |
| v0.5 | Edge AI migration (local vLLM, $0 token cost) | Planned |
| v1.0 | Slack/Zoom alerts + autonomous verbal mediation | Planned |

---

## Architecture

```
Browser (https://sentinel.bit-habit.com)
   │
   ▼
Traefik Ingress (TLS termination)
   │
   ▼
K3s Service :80 → Pod :7860
   │
   ▼
Gradio (streaming mic → 500ms chunks)
   │
   ▼
NumPy RMS → dB → HTML gauge update
```

**Future layers** (v0.1+) will add: Silero VAD → OpenAI Realtime API → emotion scoring → Sentinel Index.

---

## Quick Start

```bash
# Clone
git clone git@github.com:bookseal/sentinel-real-time-cognitive-assistant.git
cd sentinel-real-time-cognitive-assistant

# Run locally
pip install -r requirements.txt
python app.py
# Open http://localhost:7860

# Or via Docker
docker build -t sentinel:latest .
docker run -p 7860:7860 sentinel:latest
```

### Deploy to K3s

```bash
docker build -t sentinel:latest .
docker save sentinel:latest | sudo k3s ctr images import -
kubectl rollout restart deployment/sentinel
```

---

## Project Structure

```
sentinel-real-time-cognitive-assistant/
├── app.py               # Gradio app — mic streaming + volume gauge + alert
├── requirements.txt     # gradio, numpy
├── Dockerfile           # Python 3.10 slim + ffmpeg
├── CLAUDE.md            # Claude Code project instructions
├── k8s/
│   ├── deployment.yaml  # Pod spec (resources, probes)
│   ├── service.yaml     # ClusterIP :80 → :7860
│   ├── ingress.yaml     # Traefik → sentinel.bit-habit.com
│   └── secret.yaml.example
└── docs/
    ├── phase-00-guide.md              # Build, deploy, traffic flow guide
    └── 2026-03-31_1111_*.md           # Work logs
```

---

## Git Workflow

| Branch pattern | Purpose |
|---------------|---------|
| `main` | Production — deployed to K3s |
| `feature/*` | New features (`feature/persistent-alert`) |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation only |

**Tags** follow [Semantic Versioning](https://semver.org/):
`v0.0.0` (Phase 00) → `v0.1.0` (Phase 01) → ...

**Commits** follow [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Gradio 4.0+ | Native Python streaming, rapid prototyping |
| Audio | NumPy | RMS/dB calculation, zero dependencies |
| Container | Docker + Python 3.10 slim | Lightweight, reproducible |
| Orchestration | K3s on Oracle OCI | Free tier, production Kubernetes |
| Ingress | Traefik + cert-manager | Auto TLS via Let's Encrypt |
| GitOps | ArgoCD (cluster-level) | Declarative deployment |

---

Built on 42 Seoul foundations. Deployed via K3s on Oracle OCI.
