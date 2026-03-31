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

---

## Infrastructure Status Report (2026-03-31)

> Snapshot of the `bithabit` k3s cluster at the time of Phase 00 deployment.

### Cluster Overview

| Property | Value |
|----------|-------|
| Node | `bithabit` (single-node, control-plane) |
| K3s Version | v1.34.4+k3s1 |
| Container Runtime | containerd 2.1.5-k3s1 |
| Ingress Controller | Traefik 3.6.7 |
| OS | Ubuntu 20.04.6 LTS, kernel 5.15.0-1081-oracle |
| CPU | 4 cores — **44% used** (1774m / 4000m) |
| Memory | 24 Gi — **36% used** (8.7Gi / 24Gi) |
| Disk | 97 Gi — **91% used** (88Gi / 97Gi) ⚠️ CRITICAL |

### Services & Domains (15 domains via Traefik)

```
bit-habit.com              → static-web (startpage)
www.bit-habit.com          → static-web
blog.bit-habit.com         → ghost
sentinel.bit-habit.com     → sentinel (Phase 00 — this app)
argocd.bit-habit.com       → argocd-server
habit.bit-habit.com        → bithabit-api
booktoss.bit-habit.com     → booktoss
code-server.bit-habit.com  → code-server ⚠️ (broken — missing secret)
daily-seongsu.bit-habit.com → daily-seongsu
seoul-apt.bit-habit.com    → seoul-apt-price
startpage.bit-habit.com    → startpage
viz.bit-habit.com          → viz-platform
wiki.bit-habit.com         → wikijs
www.wiki.bit-habit.com     → wikijs
www.blog.bit-habit.com     → ghost
```

### Pod Health Summary

**Healthy (24 Running)**:
- `default`: sentinel, bithabit-api, booktoss, daily-seongsu, ghost, ghost-mysql,
  seoul-apt-price, startpage, static-web, wikijs-db, wikijs, viz-platform
- `argocd`: all 7 components (server, repo-server, redis, dex, etc.)
- `cert-manager`: cert-manager, cainjector, webhook
- `kube-system`: coredns, traefik, metrics-server, local-path-provisioner
- `headlamp`: 1 instance running
- `kubernetes-dashboard`: dashboard + metrics-scraper

**Problematic (~28 pods)**:

| Pod | Status | Cause |
|-----|--------|-------|
| code-server-5b6bc5dc9c-* | CreateContainerConfigError | Missing secret `code-server-secret` |
| oauth2-proxy-* (headlamp) | CreateContainerConfigError | Missing secret `oauth2-proxy-secret` |
| ~12 pods | Completed | Old finished jobs — safe to clean |
| ~8 pods | ContainerStatusUnknown | Stale after node restart |

### Resource Usage (Top Consumers)

| Service | CPU | Memory |
|---------|-----|--------|
| sentinel | 58m | 82Mi |
| wikijs | 22m | 112Mi |
| code-server | 17m | 364Mi |
| daily-seongsu | 8m | 165Mi |
| ghost | 5m | 121Mi |
| ghost-mysql | 4m | 428Mi |

### Disk & Container Images

Disk is **91% full** — k3s image garbage collection is failing.

**Largest images on disk**:

| Image | Size | Note |
|-------|------|------|
| sentinel (docker-compose build) | 5.88 GB | Old Phase 01 build — **should delete** |
| viz-bit-habit:latest | 2.81 GB | |
| booktoss:latest | 2.13 GB | |
| sentinel:latest | 1.1 GB | Current Phase 00 |
| seoul-apt-price:latest | 1.21 GB | |
| jc21/nginx-proxy-manager | 1.12 GB | Not used in k3s — **should delete** |
| code-server | 846 MB | |
| daily-seongsu | 832 MB | |
| mysql:8.0 | 782 MB | |

### ArgoCD & Cert-Manager

| Component | Status |
|-----------|--------|
| ArgoCD `bit-habit-base` | Synced, **Healthy** |
| ArgoCD `bit-habit-apps` | Synced, **Degraded** (due to code-server + oauth2-proxy failures) |
| ClusterIssuer `letsencrypt-prod` | Ready |
| Certificate `bit-habit-tls` | Ready |
| Certificate `tls-secret` | **Not Ready** ⚠️ |

### Storage

| PV | Size | Bound To | Access |
|----|------|----------|--------|
| daily-seongsu-data-pv | 1Gi | daily-seongsu-data-pvc | ReadOnlyMany |

No other persistent volumes. Most services are stateless or use in-pod storage
(ghost-mysql uses container-local storage — data loss on pod restart).

### Issues & Action Items

| # | Issue | Severity | Action |
|---|-------|----------|--------|
| 1 | **Disk 91% full**, image GC failing | CRITICAL | Delete old sentinel 5.88GB image, nginx-proxy-manager, dangling images |
| 2 | **code-server** broken (missing secret) | HIGH | Create `code-server-secret` or remove deployment |
| 3 | **oauth2-proxy** broken (missing secret) | HIGH | Create `oauth2-proxy-secret` or remove deployment |
| 4 | **~28 stale pods** (Completed/Unknown) | MEDIUM | `kubectl delete pod --field-selector=status.phase==Succeeded -A` |
| 5 | **tls-secret** certificate not ready | MEDIUM | Check cert-manager logs, may need re-issue |
| 6 | **ArgoCD bit-habit-apps** degraded | LOW | Will self-heal once #2 and #3 are fixed |
| 7 | **ghost-mysql** has no persistent volume | LOW | Data loss risk on pod restart — add PVC if data matters |

### Quick Remediation Commands

```bash
# 1. Free disk space — delete old sentinel build image
docker rmi sentinel-real-time-cognitive-assistant-sentinel:latest

# 2. Delete unused nginx-proxy-manager
docker rmi jc21/nginx-proxy-manager:latest

# 3. Prune all dangling images (Docker + k3s)
docker image prune -f
sudo k3s crictl rmi --prune

# 4. Clean up stale pods
kubectl delete pod --field-selector=status.phase==Succeeded -A
kubectl delete pod --field-selector=status.phase==Failed -A

# 5. Check disk after cleanup
df -h /

# 6. Verify cert-manager issue
kubectl describe certificate tls-secret
kubectl logs deployment/cert-manager -n cert-manager --tail=20
```
