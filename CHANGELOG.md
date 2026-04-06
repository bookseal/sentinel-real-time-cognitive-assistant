# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
