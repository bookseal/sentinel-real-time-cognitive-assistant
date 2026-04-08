# TODOS

## Pending

### Update bit-habit-infra resource limits
- **Why:** K8s manifests in the infra repo (bookseal/bit-habit-infra) still have v0.1 limits (512Mi/1Gi). v0.2 needs ~768Mi request / 1.5Gi limit for Silero VAD model.
- **Context:** The k8s/ manifests in this repo are reference-only. Real deployment is managed by ArgoCD from bit-habit-infra. Update `apps/sentinel/deployment.yaml` there.
- **Blocked by:** v0.2 code merged to main.

### Update design doc to reflect OpenAI pivot
- **Why:** The design doc at `~/.gstack/projects/` still describes the SpeechBrain wav2vec2 approach. Should reflect the pivot to OpenAI Realtime API.
- **Context:** The plan file (`~/.claude/plans/lively-floating-quill.md`) has the accurate architecture. The design doc update is a documentation task.
