# =============================================================================
# Dockerfile — Blueprint for building the Sentinel container image
#
# Think of it as a recipe:
#   1. Start from a base image (Python 3.10)
#   2. Install OS-level packages (ffmpeg)
#   3. Install Python packages (gradio, numpy)
#   4. Copy app code
#   5. Set defaults (env vars, port)
#   6. Define startup command
#
# Build:  docker build -t sentinel:latest .
# Run:    docker run -p 7860:7860 sentinel:latest
# =============================================================================

# --- Base Image ---------------------------------------------------------------
# Start from official Python 3.10 slim (Debian-based, ~150MB)
# "slim" = minimal OS packages, smaller than full "python:3.10" (~900MB)
FROM python:3.10-slim

# --- Working Directory --------------------------------------------------------
# All subsequent commands (COPY, RUN, CMD) run inside /app
# Like: mkdir -p /app && cd /app
WORKDIR /app

# --- OS Dependencies ----------------------------------------------------------
# ffmpeg: audio format conversion — Gradio uses it internally for mic input
# rm -rf /var/lib/apt/lists/*: delete apt cache to keep image size small
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# --- Python Dependencies -----------------------------------------------------
# COPY requirements.txt first (before app code) for Docker layer caching:
#   If requirements.txt hasn't changed, Docker skips the pip install step
#   on rebuild — saves minutes of download time
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- App Code -----------------------------------------------------------------
# COPY everything from current directory (.) into /app inside the container
# This includes: app.py, k8s/, docs/, etc.
COPY . .

# --- Environment Variables ----------------------------------------------------
# These are defaults — can be overridden at runtime (docker run -e or K8s envFrom)
# GRADIO_SERVER_NAME: listen on all interfaces (not just localhost)
# GRADIO_SERVER_PORT: Gradio's HTTP port
# PYTHONUNBUFFERED:   don't buffer stdout — logs appear immediately
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"
ENV PYTHONUNBUFFERED="1"

# --- Expose Port --------------------------------------------------------------
# Documentation only — tells readers "this container listens on 7860"
# Does NOT actually open the port (that's done by -p flag or K8s Service)
EXPOSE 7860

# --- Startup Command ----------------------------------------------------------
# What runs when the container starts
# Equivalent to: python app.py
CMD ["python", "app.py"]
