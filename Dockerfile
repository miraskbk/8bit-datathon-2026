# NVIDIA/Linux deployment: supply local model files and cached detector weights.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/models/huggingface
WORKDIR /service
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY app ./app
COPY artifacts ./artifacts
COPY docs ./docs
COPY third_party ./third_party
COPY tools/download_event_models.py ./tools/download_event_models.py
RUN pip install --no-cache-dir .
# Setup downloads model weights only, before any private recordings are present.
RUN python tools/download_event_models.py --vlm transformers
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
    PIPELINE=cashguard VLM_BACKEND=transformers VLM_MODEL=/service/models/Qwen3-VL-4B-Instruct PRELOAD_MODEL=true
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
