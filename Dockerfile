# =============================================================================
# Dockerfile — Sentinel v0.2 container image
#
# v0.2 adds Silero VAD (ONNX, ~2MB) and OpenAI API client.
# No PyTorch needed — silero-vad uses onnxruntime.
# Image stays small (~400MB vs ~1.4GB if we'd used PyTorch).
#
# Build:  docker build -t sentinel:latest .
# Run:    docker run -p 7860:7860 -e OPENAI_API_KEY=sk-... sentinel:latest
# =============================================================================

FROM python:3.10-slim

WORKDIR /app

# ffmpeg for Gradio audio processing
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Python deps (silero-vad pulls onnxruntime, not full PyTorch)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"
ENV PYTHONUNBUFFERED="1"

EXPOSE 7860

CMD ["python", "app.py"]
