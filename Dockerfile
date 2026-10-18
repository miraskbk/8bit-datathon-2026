# Build requires internet for packages/weights only. Runtime inference is offline.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/models/huggingface \
    UV_LINK_MODE=copy PATH=/service/.venv/bin:$PATH
WORKDIR /service
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.23
COPY pyproject.toml uv.lock README.md ./
COPY app ./app
COPY artifacts ./artifacts
COPY docs ./docs
COPY third_party ./third_party
COPY tools/download_event_models.py ./tools/download_event_models.py
RUN uv sync --locked --no-dev
RUN python tools/download_event_models.py --vlm transformers
RUN groupadd --gid 10001 review && useradd --uid 10001 --gid review --no-create-home review \
    && mkdir -p /service/runtime/jobs /service/runtime/tmp /service/runtime/visioncore \
    && chown -R review:review /service/runtime \
    && chmod -R 700 /service/runtime
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
    PIPELINE=visioncore VLM_BACKEND=transformers VLM_MODEL=/service/models/Qwen3-VL-4B-Instruct \
    PRELOAD_MODEL=true TMPDIR=/service/runtime/tmp XDG_CACHE_HOME=/service/runtime/cache
USER review
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
