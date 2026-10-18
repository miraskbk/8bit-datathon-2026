# 8bit — local cash-discipline video review

A local web UI and authenticated API for reviewing MOV videos. The integrated
CashGuard pipeline returns possible violations, timestamps, 1–3 JPEG evidence
frames and Kazakhstan rule references. A person must review each result.

## Teammate quick start: Apple Silicon Mac

Use Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/).
The tested machine has 24 GB unified memory. Allow at least 10 GB for model
weights. A smaller Mac may run out of memory. Models are downloaded separately;
no videos, shared API keys or private reports are included in this branch.

```bash
git clone --branch teammate-test --single-branch https://github.com/miraskbk/8bit-datathon-2026.git
cd 8bit-datathon-2026
uv sync --extra mlx --extra dev
.venv/bin/python -m tools.setup_local --backend mlx
.venv/bin/python -m tools.download_event_models --vlm mlx
.venv/bin/python -m tools.start_local_service
```

Wait for `Application startup complete`, then open **http://127.0.0.1:8003**.
Copy your locally generated key from `runtime/jury-access.txt` into the
**X-API-Key** field. Upload your own MOV video. Keep Terminal open; Ctrl+C stops
the server. On later runs, only the final command is needed. The setup command
preserves an existing `.env` and does not print or publish the key.

Initial model download needs internet and can take time. Once weights are
installed, inference uses local files with offline loading enabled. No video,
frame or scene description is sent to a cloud AI service. No audio or face
identification is used. A GitHub push shares code; it does not host this app.

## Linux with an NVIDIA GPU

The Transformers backend uses the original Qwen3-VL-4B checkpoint. Install a
CUDA-compatible PyTorch build/driver and provision sufficient GPU memory (at
least 16 GB recommended). This backend needs a latency/accuracy check on its
own host; Mac MLX measurements do not establish Linux/CUDA performance.

```bash
uv sync --extra dev
.venv/bin/python -m tools.setup_local --backend transformers
.venv/bin/python -m tools.download_event_models --vlm transformers
.venv/bin/python -m tools.start_local_service
```

A Docker recipe is also included. It downloads weights at build time and must
be given a private `API_KEY` at runtime. The image requires NVIDIA GPU support;
it has not been smoke-tested on this Mac.

## API and limits

- UI: `/`; API docs: `/docs`; readiness: `/health`.
- `POST /api/v1/analyze`: multipart `file`, MOV, returns `job_id` (HTTP 202).
- `GET /api/v1/jobs/{job_id}`: `processing`, `done` or `failed` and result.
- Both jury endpoints require `X-API-Key`. Use your own generated local key.
- Defaults: 35 MiB, 180 seconds, one accepted job at a time, 270-second deadline.
- Capacity rejection is HTTP 429. Bad/empty/oversized uploads are rejected.
- Videos are deleted after processing; private results/evidence expire after an hour.

```bash
export JURY_API_KEY='<your local key>'
curl -X POST http://127.0.0.1:8003/api/v1/analyze \
  -H "X-API-Key: $JURY_API_KEY" -F 'file=@your-video.mov'
curl http://127.0.0.1:8003/api/v1/jobs/<job_id> \
  -H "X-API-Key: $JURY_API_KEY"
```

For one completed local job, inspect its verdict, source link, timestamp and
frames in the UI. `no_violation` means no supported indicator was found; it
does not certify compliance with every bank rule. Unlocalized regions and
unreadable states are disclosed as limited coverage. Model failures return
`failed`, never a fabricated clean verdict.

## Tests and measured limits

```bash
.venv/bin/python -m pytest -q
```

Tests use synthetic inputs and do not load models or require organizer footage.
For a real HTTP smoke test after starting the app:

```bash
.venv/bin/python -m tools.smoke_http your-video.mov \
  --output local-evaluation/my-smoke.json
```

The integrated Mac pipeline processed all 40 unique organizer videos: **80%**
video accuracy, **14/21** positives detected and **1/19** negative false alarms.
Median processing time was **20.88 s**, maximum **120.71 s**. These are development
regression results: the imported state classifiers were trained on organizer
footage, so they do not establish unseen-camera accuracy. Document return,
transaction completion, permissions and bookkeeping are not verified. Occlusion,
reflections, small objects and different viewpoints can cause errors.

## Attribution and competition eligibility

The full MIT-licensed CashGuard detection/scene/state/rule pipeline and two small
trained classifiers are included. Pretrained detectors, DINOv2 and Qwen model
weights are installed separately. See [integration notes](docs/CASHGUARD_INTEGRATION.md),
[MIT license](third_party/CASHGUARD_LICENSE), and
[provenance](third_party/CASHGUARD_NOTICE.md). Regulatory source details are in
[the source registry](docs/npa_registry.md) and
[screen-lock interpretation](docs/npa_workstation_lock.md).

The hackathon's FAQ 35 prohibits ready-made solutions. MIT licensing permits
reuse but does not resolve competition eligibility; organizer clarification is
still needed. Keep `.env`, `runtime/`, footage, labels and local evaluation
reports out of Git. Public jury access requires a separately deployed HTTPS URL.
