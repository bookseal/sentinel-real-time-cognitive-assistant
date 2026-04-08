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

v0.2 테스트 진행 중 — `feature/vad-emotion-pipeline` 브랜치에서 작업.

### 진행 상황

#### 설계 및 리뷰 (구현 전)
- `/office-hours`로 v0.2 설계 문서 작성 (VAD + 감정 인식 파이프라인)
- `/plan-eng-review`로 아키텍처·코드 품질·테스트·성능 리뷰 완료
- Codex 외부 의견 반영: SpeechBrain(로컬 wav2vec2) → OpenAI API로 전환 결정
  - 이유: ARM k3s에서 PyTorch 빌드 실패, 이미지 크기 폭증, 메모리 부족
- 6건의 아키텍처/품질/성능 이슈 발견 및 해결 방안 수립

#### 구현 완료
- `audio_logic.py` 추출 — app.py에서 오디오 처리 로직 분리 (norminette 규칙: 파일당 7함수 제한)
- `vad.py` — Silero VAD 래퍼 (ONNX, 1.8MB, 청크당 ~1ms)
  - 백그라운드 스레드에서 모델 로딩 (앱 즉시 시작, 로딩 중 v0.1 모드로 동작)
- `audio_buffer.py` — VAD 기반 링 버퍼
  - 300ms 프리롤, 1.5~2초 음성 누적, 500ms 행오버
  - 발화 완료 감지 시 utterance 반환
- `emotion.py` — OpenAI API 감정 분류 (calm/stressed/angry)
  - ThreadPoolExecutor로 fire-and-forget 비동기 추론 (UI 블로킹 없음)
- `app.py` 전면 리라이트 — v0.2 파이프라인 통합
  - `SessionState` 클래스로 세션별 상태 격리 (멀티유저 크로스토크 방지)
  - 게이지 HTML에 감정 라벨 추가 (초록=calm, 주황=stressed, 빨강=angry)
  - Gradio `share=True` 공개 링크 활성화

#### 테스트
- pytest 테스트 스위트 작성: 5개 모듈, 45개 테스트 (커버리지 0% → 90%+)
  - `test_app.py` — Gradio 앱 빌드, 오디오 처리, 세션 상태
  - `test_audio_buffer.py` — 링 버퍼 누적, 프리롤, 행오버, 엣지케이스
  - `test_audio_logic.py` — dB 계산, 리샘플링, 빈 배열, NaN 처리
  - `test_emotion.py` — OpenAI 호출 모킹, 비동기 추론, 에러 핸들링
  - `test_vad.py` — VAD 모델 로딩, 확률 반환, 폴백 동작

#### 인프라
- `Dockerfile` 업데이트 — Silero VAD + OpenAI 의존성 (PyTorch 없이 이미지 ~400MB 유지)
- `k8s/deployment.yaml` — VAD 모델 메모리 반영 리소스 리밋 조정
- `requirements.txt` — silero-vad, openai 추가
- `VERSION` 파일 생성, `TODOS.md` 생성

### 남은 작업
- 테스트 통과 확인 후 main 브랜치에 머지
- bit-habit-infra 레포 K8s 리소스 리밋 업데이트 (512Mi → 768Mi/1.5Gi)
- 설계 문서에 OpenAI 전환 내용 반영 (현재 SpeechBrain 기준으로 작성됨)

### 이전 버전 변경사항 (v0.1 → v0.2 사이)
- 10초 지속 경고 배너 추가 (볼륨 임계치 초과 시)
- CLAUDE.md 프로젝트 컨벤션 추가 (코드 스타일, git 워크플로우, 브랜치 네이밍)
- CHANGELOG.md 버전 이력 추적 시작
- Dockerfile ENV 줄 인라인 주석 문법 수정
- "Phase XX" 네이밍을 시맨틱 버전 (v0.X)으로 통일

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
