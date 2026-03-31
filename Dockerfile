FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (ffmpeg for Gradio audio handling)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"
ENV PYTHONUNBUFFERED="1"

EXPOSE 7860

CMD ["python", "app.py"]
