# Phase 00 — Minimal Volume Gauge: Complete Guide

## What is Phase 00?

A minimal Gradio web app that streams microphone audio and displays a real-time
volume (dB) gauge in the browser. No AI, no cloud API, no VAD — just NumPy RMS.

## Project Structure

```
sentinel-real-time-cognitive-assistant/
├── app.py                  # Gradio app (the only code that runs)
├── requirements.txt        # Python deps: gradio, numpy
├── Dockerfile              # How to build the container image
├── k8s/
│   ├── deployment.yaml     # Pod spec (what container to run, resources)
│   ├── service.yaml        # Internal load balancer (port mapping)
│   ├── ingress.yaml        # External access (domain + TLS)
│   └── secret.yaml.example # Template for API keys
└── docs/
```

---

## The Full Flow: Code → Browser

### Step 1: Write the app (`app.py`)

```
app.py (Python)
  └── Gradio streams mic audio
  └── NumPy computes RMS → dB
  └── Returns HTML gauge to browser
```

### Step 2: Build a Docker image (`Dockerfile`)

The Dockerfile packages `app.py` + dependencies into a portable image.

```bash
docker build -t sentinel:latest .
```

What happens inside:
```
python:3.10-slim          # base OS + Python
  └── apt install ffmpeg  # audio codec (for Gradio)
  └── pip install gradio numpy
  └── COPY app.py etc.
  └── CMD python app.py   # runs on container start
```

Result: a **Docker image** named `sentinel:latest` stored locally.

### Step 3: Import image into k3s (`docker save | k3s ctr import`)

k3s uses **containerd** (not Docker) as its container runtime.
Docker and containerd have separate image stores — they can't see each other.

```bash
# Export from Docker → Import into containerd (k3s)
docker save sentinel:latest | sudo k3s ctr images import -
```

```
┌──────────────┐     docker save     ┌───────────────┐
│ Docker daemon │ ──── .tar ────────► │ k3s containerd │
│ (build tool)  │                     │ (runtime)      │
└──────────────┘                     └───────────────┘
```

### Step 4: Deploy to k3s (Kubernetes manifests)

Apply the three YAML files — they tell k3s what to run and how to expose it:

```bash
kubectl apply -f k8s/deployment.yaml   # "run 1 pod with sentinel:latest"
kubectl apply -f k8s/service.yaml      # "expose pod port 7860 as port 80"
kubectl apply -f k8s/ingress.yaml      # "route sentinel.bit-habit.com → service"
```

Or, to update an existing deployment after a new image build:
```bash
kubectl rollout restart deployment/sentinel
```

### Step 5: Traffic reaches the app

```
Browser (https://sentinel.bit-habit.com)
   │
   ▼
DNS → resolves to server IP
   │
   ▼
Traefik Ingress Controller (port 443)
   │  ← TLS termination (Let's Encrypt cert via cert-manager)
   │  ← Matches host: sentinel.bit-habit.com
   ▼
Service: sentinel-svc (port 80)
   │  ← selector: app=sentinel → finds matching pods
   ▼
Pod: sentinel-xxx (port 7860)
   │  ← container runs: python app.py
   ▼
Gradio serves HTML + opens WebSocket for mic streaming
   │
   ▼
Browser renders volume gauge, updated every ~500ms
```

---

## Common Operations

### Build & Deploy (full cycle)

```bash
# 1. Build image
docker build -t sentinel:latest .

# 2. Import into k3s
docker save sentinel:latest | sudo k3s ctr images import -

# 3. Restart deployment (picks up new image)
kubectl rollout restart deployment/sentinel

# 4. Watch rollout
kubectl rollout status deployment/sentinel
```

### Check if it's running

```bash
# Pod status (should be Running, Ready 1/1)
kubectl get pods -l app=sentinel

# Pod logs (look for "Starting Sentinel Phase 00")
kubectl logs deployment/sentinel --tail=10

# Service endpoint
kubectl get endpoints sentinel-svc

# Ingress routing
kubectl get ingress sentinel-ingress
```

### Debug a failing pod

```bash
# Detailed pod info + events (image pull errors, OOM, eviction)
kubectl describe pod -l app=sentinel

# Live log stream
kubectl logs -f deployment/sentinel

# Shell into the running container
kubectl exec -it deployment/sentinel -- bash
```

### Clean up disk space

```bash
# Remove dangling Docker images (untagged leftovers from previous builds)
docker image prune -f

# Remove unused k3s images
sudo k3s crictl rmi --prune

# Check disk
df -h /
```

---

## Key Concepts for Beginners

### Docker image vs Container
- **Image** = a snapshot (like a `.iso` file). Built once, read-only.
- **Container** = a running instance of an image (like a VM booted from the `.iso`).

### Kubernetes objects (the 3 YAMLs)
| Object | What it does | Real-world analogy |
|--------|-------------|-------------------|
| **Deployment** | "Run N copies of this container" | A job posting ("hire 1 Python dev") |
| **Service** | "Give these pods a stable address" | A phone number that routes to whoever is on-call |
| **Ingress** | "Route external traffic to a Service" | A receptionist ("sentinel.bit-habit.com? → dial extension 80") |

### Port chain
```
Browser :443 → Ingress (TLS) → Service :80 → Pod :7860 → Gradio app
```

### imagePullPolicy: Never
In `deployment.yaml`, this means "don't try to pull from Docker Hub — the image
is already on this machine." That's why we manually import with `k3s ctr images import`.

### Why k3s, not Docker Compose?
- Docker Compose: single-machine dev tool. No TLS, no health checks, no auto-restart.
- k3s: lightweight Kubernetes. Handles TLS (cert-manager), health probes, rolling updates,
  resource limits, and can scale to multiple machines later.
