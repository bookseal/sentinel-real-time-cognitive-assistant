# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0.0] - 2026-04-08

VAD-gated emotion detection. Sentinel can now tell the difference between a cough and an argument.

### Added
- Voice Activity Detection via Silero VAD (ONNX, 1.8MB, ~1ms per chunk)
- Emotion classification via OpenAI API (calm/stressed/angry)
- Per-session state isolation (SessionState class) for multi-user support
- Ring buffer with 300ms pre-roll, 1.5-2s voiced accumulation, 500ms hangover
- Background VAD model loading (app starts instantly, degrades to v0.1 while loading)
- Fire-and-forget emotion inference in ThreadPoolExecutor (non-blocking UI)
- Emotion label in gauge HTML (color-coded: green=calm, orange=stressed, red=angry)
- Full pytest test suite: 45 tests across 5 modules (0% to 90%+ coverage)
- TODOS.md for tracking deferred work
- VERSION file for semantic versioning

### Changed
- Extracted `audio_logic.py` from app.py (norminette: max 7 functions per file)
- Rewritten app.py: v0.2 pipeline, cleaned teaching comments, updated header diagram
- Dockerfile updated for Silero VAD + OpenAI (no PyTorch, image stays ~400MB)
- K8s deployment.yaml resource limits updated for VAD model memory
- requirements.txt: added silero-vad, openai

### Fixed
- Resample function now handles empty arrays and invalid sample rates
- Audio buffer copies chunks to prevent mutation by caller
- WAV encoding clips audio to [-1, 1] and handles NaN/Inf

## [Unreleased]

### Added
- Persistent 10-second alert banner when volume exceeds warning/alert thresholds
- CLAUDE.md with project conventions (code style, git workflow, branch naming)
- CHANGELOG.md for version history tracking

### Fixed
- Dockerfile inline comment syntax on ENV lines

### Changed
- Replaced "Phase XX" naming with semantic versions (v0.X) across all docs and code
- Standardized git workflow conventions

## [0.0.0] - 2026-03-31

First working deployment. Minimal volume gauge on K3s (Oracle OCI).

### Added
- Real-time browser microphone → volume (dB) gauge pipeline
- Color-coded gauge: green (<60 dB) / yellow (60–70 dB) / red (≥70 dB)
- Gradio 4.0+ streaming UI with NumPy RMS computation
- Dockerfile for containerized deployment (Python 3.10-slim + ffmpeg)
- K8s manifests for k3s deployment (Deployment, Service, Ingress)
- Build/deploy guide (`docs/guide-v0.0-volume-gauge.md`)
- Request lifecycle documentation (`docs/guide-request-lifecycle.md`)
- Infrastructure status work log

### Fixed
- Korean Gradio UI strings forced to English via JS injection
- CSS transitions causing waveform flicker

### Security
- Removed `secret.yaml` from git history, added `.gitignore` and template

[Unreleased]: https://github.com/bookseal/sentinel-real-time-cognitive-assistant/compare/v0.0.0...HEAD
[0.0.0]: https://github.com/bookseal/sentinel-real-time-cognitive-assistant/releases/tag/v0.0.0
