FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/huggingface

WORKDIR /service
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY app ./app
COPY artifacts ./artifacts
RUN pip install --no-cache-dir .
# Bake the pretrained temporal encoder into the image. Runtime inference stays offline.
RUN python -c "from torchvision.models.video import R3D_18_Weights, r3d_18; r3d_18(weights=R3D_18_Weights.DEFAULT)"
ENV HF_HUB_OFFLINE=1 \
    PRELOAD_MODEL=true

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
