# 2026-03-31 11:11 — v0.0: Minimal Volume Gauge Deploy

## What was done

- Created branch `feature/v0.0-minimal-volume` from `feature/v0.1-volume-guard`
- Replaced `app.py` with a minimal ~120-line version: mic button + real-time volume (dB) gauge only
- Stripped `requirements.txt` to `gradio` + `numpy` (removed torch, torchaudio, websockets, python-dotenv)
- Simplified `Dockerfile` (removed Silero VAD download, removed gcc)
- Built Docker image, imported into k3s containerd, restarted deployment
- Cleaned dangling Docker images (reclaimed ~2 GB) to fix ephemeral-storage eviction

## Why

v0.1 deployed successfully (pod Running) but the full feature set (VAD, pitch, streaming) was not functional in the k3s environment. A minimal v0.0 was needed to validate the basic pipeline: mic → volume gauge.

## Files changed

| File | Change |
|------|--------|
| `app.py` | Full rewrite — minimal volume gauge (~120 lines) |
| `requirements.txt` | `gradio>=4.0`, `numpy` only |
| `Dockerfile` | Removed torch/VAD steps, removed gcc |

## Verification commands

```bash
# 1. Check pod status (should be Running, Ready 1/1)
kubectl get pods -l app=sentinel

# 2. Check logs for "v0.0" startup message
kubectl logs deployment/sentinel --tail=10

# 3. Describe pod for events (look for eviction or image errors)
kubectl describe pod -l app=sentinel | tail -20

# 4. Curl the service internally
kubectl run curl-test --rm -it --image=curlimages/curl --restart=Never -- curl -s http://sentinel-svc/

# 5. Check from browser
#    Open https://sentinel.bit-habit.com
#    Click mic button → volume gauge should move in real-time

# 6. Check ingress routing
kubectl get ingress sentinel-ingress

# 7. Check service endpoint
kubectl get endpoints sentinel-svc

# 8. Check disk space (was the cause of eviction)
df -h /

# 9. Check Docker image size
docker images sentinel:latest --format '{{.Repository}}:{{.Tag}} {{.Size}}'

# 10. Check k3s containerd images
sudo k3s crictl images | grep sentinel
```
