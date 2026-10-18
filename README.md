# 8bit: cash-discipline video review

8bit reviews MOV video for visible indicators of possible cash-discipline violations. A reviewer receives a verdict, event timestamps, 1–3 JPEG evidence frames per event, an observation, and a Kazakhstan regulatory source. All AI inference runs inside the team's service. The result supports human review.

**Release status:** the application, jury API, local setup and deployment configuration are provided. **No public demo is deployed yet.** The team must provision a GPU host/domain, verify it from an external connection and provide a private jury key before submission. Linux/CUDA deployment performance remains unverified. This release is a reviewable deployment candidate, not evidence of a live production service.

- [Local demo setup](#local-demo-on-apple-silicon)
- [Public HTTPS deployment and jury handoff](docs/DEPLOYMENT.md)
- [Jury API contract](#jury-api)
- [Requirement and evaluation checklist](docs/JURY_REQUIREMENTS.md)
- [Architecture and integration](docs/ARCHITECTURE.md)
- [Pitch deck and speaker guide](pitch/README.md)

## Local demo on Apple Silicon

The tested environment is an Apple Silicon Mac with 24 GB unified memory, Python 3.12, and the MLX backend. Smaller machines may run out of memory. Reserve at least 10 GB for model downloads plus space for Python dependencies. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/miraskbk/8bit-datathon-2026.git
cd 8bit-datathon-2026
uv sync --locked --extra mlx --extra dev
.venv/bin/python -m tools.setup_local --backend mlx
.venv/bin/python -m tools.download_event_models --vlm mlx
.venv/bin/python -m tools.start_local_service
```

Wait for `Application startup complete`, then open [the local demo](http://127.0.0.1:8003). This link works on the machine running the server. Copy the newly generated key from `runtime/jury-access.txt` into **X-API-Key**, select your own `.mov` or `.MOV`, and choose **Запустить анализ**. The page shows readiness, limits, processing status and the job ID. Click an event time to seek the preview and an evidence image to download its full JPEG. Some MOV codecs cannot play in a browser, but the server can still accept a decodable video.

Keep the terminal open. Ctrl+C stops the server. On later runs:

```bash
cd 8bit-datathon-2026
.venv/bin/python -m tools.start_local_service
```

The setup command creates a different random key for each checkout, writes private configuration with mode `0600`, and preserves an existing `.env`. The key remains only in page memory and disappears when the page reloads. Share a deployed service's key privately with the jury, never through a README or a URL.

Initial installation/download needs internet. After weights are installed, model loading uses local files with offline flags. Inference never calls cloud LLM, recognition or multimodal APIs. Organizer recordings, annotations, evidence and private reports are excluded from Git.

## Linux and NVIDIA GPU

Use Python 3.12 and a CUDA-compatible PyTorch/driver environment. The Transformers backend uses Qwen3-VL-4B. Provision enough VRAM for **all** models, not just Qwen; 16 GB is a starting estimate, not a measured guarantee. Benchmark memory, accuracy and the five-minute deadline on the actual host.

```bash
uv sync --locked --extra dev
.venv/bin/python -m tools.setup_local --backend transformers
.venv/bin/python -m tools.download_event_models --vlm transformers
.venv/bin/python -m tools.start_local_service
```

This launcher binds to loopback on port 8003. For a public jury service use the [Docker Compose and HTTPS deployment guide](docs/DEPLOYMENT.md). Docker builds download packages and model weights only. The runtime configuration isolates the inference container from external networks. The Docker/GPU stack has not been executed on this Mac and must pass the host checks in that guide before use.

## Jury API

The deployed UI and API share one HTTPS origin. Local examples use port 8003. `/docs` is a locally served API guide without external JavaScript/CDN dependencies; `/openapi.json` is the machine-readable contract.

| Method | Path | Access | Behavior |
| --- | --- | --- | --- |
| GET | `/` | Public | Video upload and results UI |
| GET | `/docs` | Public | Jury instructions and examples |
| GET | `/openapi.json` | Public | OpenAPI schema with `X-API-Key` security |
| GET | `/health` | Public | Diagnostic model readiness |
| GET | `/ready` | Public | HTTP 200 when models are loaded, otherwise 503 |
| GET | `/api/v1/capabilities` | Public | Active limits and local-only capabilities |
| POST | `/api/v1/analyze` | `X-API-Key` | Multipart `file`, MOV. HTTP 202 with `job_id` |
| GET | `/api/v1/jobs/{job_id}` | `X-API-Key` | Status `processing`, `done` or `failed` and result |

### Upload and poll

Set the origin to the team's deployed domain for jury testing. Enter the key without writing its value into shell history:

```bash
export SERVICE_URL='http://127.0.0.1:8003'
read -r -s JURY_API_KEY
export JURY_API_KEY
curl --fail-with-body -X POST "$SERVICE_URL/api/v1/analyze" \
  -H "X-API-Key: $JURY_API_KEY" -F 'file=@your-video.mov'
```

Example accepted response:

```json
{"job_id":"3f2a9c1e3f2a9c1e3f2a9c1e3f2a9c1e","status":"processing"}
```

Use the returned ID and poll about every two seconds:

```bash
curl --fail-with-body \
  "$SERVICE_URL/api/v1/jobs/3f2a9c1e3f2a9c1e3f2a9c1e3f2a9c1e" \
  -H "X-API-Key: $JURY_API_KEY"
```

Example completed response shape below uses placeholder evidence, not an actual detection:

```json
{
  "job_id": "3f2a9c1e3f2a9c1e3f2a9c1e3f2a9c1e",
  "status": "done",
  "verdict": "violation",
  "violations": [{
    "type": "Observed event category",
    "timecode_sec": 44.2,
    "description": "Visible observation and why a person should check it",
    "evidence_frames": [{
      "timestamp_sec": 44.2,
      "image_base64": "<actual JPEG encoded as base64 in a real response>"
    }],
    "rule": {
      "document": "Kazakhstan regulatory document",
      "section": "Point or section",
      "url": "https://adilet.zan.kz/rus/docs/..."
    }
  }],
  "metadata": {"local_only": true, "warnings": []},
  "error": null
}
```

`no_violation` returns `violations: []`. Processing and failed jobs have `verdict: null`. Errors never become a fabricated clean result. `rule`, `metadata`, `confidence` and `error` are extensions to the mandatory jury fields. Evidence frames use plain base64 JPEG bytes, without a data-URL prefix. Timestamps are seconds from video start. A positive result can contain several events.

### Limits and recovery

| Condition | Default / response |
| --- | --- |
| File | MOV, up to 35 MiB (36,700,160 bytes) |
| Duration | Up to 180 seconds, known positive duration |
| Resolution | Width × height up to 8,294,400 pixels |
| Accepted jobs | One at a time, model process reused between jobs |
| Deadline | 270 seconds from upload-handler start, including validation and queue wait |
| Jury deadline | 5 minutes end to end. Slow upload/network time also matters |
| Retention | Results/evidence expire after one hour; cleanup runs at least every 60 seconds |
| Missing/wrong key | HTTP 401, rejected before protected request-body parsing |
| Missing/expired job | HTTP 404 |
| Oversized request/file | HTTP 413 |
| Wrong extension | HTTP 415 |
| Invalid/empty/unsupported MOV or exceeded metadata limits | HTTP 422 |
| Capacity full | HTTP 429, `Retry-After: 15` |
| Worker failure/timeout | Poll returns `status: failed`, with no verdict |

The request-body guard allows 1 MiB above the file limit for multipart overhead and checks streamed bodies without relying on `Content-Length`. The reverse proxy uses the same 36 MiB complete-request ceiling. A stalled model process is terminated and recreated for the next job. Only one API process can own a job directory: **use `--workers 1` and one app replica per runtime volume**. Persistent completed results survive restarts; interrupted jobs become failed and require re-upload. If the connection drops after a job ID arrives, continue polling it or use **Повторно получить результат** in the UI.

## Configuration

Copy/setup `.env` privately. Environment variables override its values. Paths are resolved relative to the repository unless absolute. See [.env.example](.env.example).

| Variable | Meaning |
| --- | --- |
| `API_KEY` | Private key, at least 32 characters; generate with setup tool |
| `VLM_BACKEND` | `mlx` on Apple Silicon or `transformers` on Linux/CUDA |
| `VLM_MODEL` | Local Qwen checkpoint directory, matching selected backend |
| `DEVICE` | Optional PyTorch device, otherwise CUDA/MPS/CPU selected locally |
| `JOB_DIR` | Private persisted job directory |
| `PRELOAD_MODEL` | Keep `true` for jury deployment so startup verifies weights |
| `MAX_VIDEO_MB` | File cap in MiB, default 35 |
| `MAX_DURATION_SECONDS` | Video duration cap, default 180 |
| `MAX_VIDEO_PIXELS` | Frame width × height cap, default 8,294,400 |
| `ANALYSIS_TIMEOUT_SECONDS` | Worker deadline, default 270, allowed 30–290 |
| `MAX_PENDING_JOBS` | Total accepted running/waiting jobs, default 1; raising it can consume the deadline |
| `JOB_TTL_SECONDS` | Result/evidence retention, default 3600, minimum 300 |
| `ALLOWED_HOSTS` | JSON list of permitted hostnames. Include the public domain and loopback health host |
| `DEMO_DOMAIN` | Docker HTTPS gateway's public DNS hostname |

## Architecture

The browser and jury use the same FastAPI endpoints. The API checks the key and upload limits, validates MOV metadata/decoding, persists a random job ID, and dispatches work to a supervised local process. The process runs:

1. RT-DETRv2 and OWLv2 for people, objects and scene regions.
2. Scene geometry and anonymous tracks for temporal event candidates.
3. Frozen DINOv2 features plus the imported safe/cash state classifiers.
4. Selected local Qwen screen/door questions, capped at 12 per video.
5. Temporal rules, deduplication, timestamp selection and 1–3 annotated JPEGs per event.
6. An adapter adds regulatory references, coverage warnings and cautious observation language to the jury result.

The Mac backend uses Qwen3-VL-8B in MLX 4-bit format. Linux uses Qwen3-VL-4B with Transformers, so results can differ. Model revisions are pinned in `tools/download_event_models.py`; downloads require Apache-2.0 model metadata. Classifier/source hashes and the copied source commit are recorded in [provenance](third_party/pipeline-provenance.json). No audio or biometric face identification is used.

## Event coverage and regulatory basis

The enabled pipeline checks the following visible indicators. Rule matches support investigation and do not establish every legal precondition.

| Code | Visible indicator | Regulatory relationship |
| --- | --- | --- |
| A | Objects resembling valuables remain after departure | Rules № 231, points 20/22, context dependent |
| B | Safe appears open after a person moves away | Rules № 231, points 20/80, indirect |
| C | Cash-like objects on desk as another visitor appears | Rules № 231, point 20; ownership/transaction context unknown |
| E | Additional person or person behind the cashier desk | Rules № 14, points 8/16; permissions unknown |
| F | Short visible bag handoff before departure | Rules № 231, points 24/25; off-camera inspection unknown |
| G | Personal items or drink interaction in work zone | Rules № 231, point 12; drink relation indirect |
| H | Door appears open after entry | Rules № 14, points 8/16, indirect |
| L | Screen appears active after departure | Requirements № 53, points 26/71, indirect |

Public Kazakhstan source links: [Rules № 231](https://adilet.zan.kz/rus/docs/V1900019680), [Rules № 14](https://adilet.zan.kz/rus/docs/V2000020075), [Requirements № 53](https://adilet.zan.kz/rus/docs/V2600038336). The bundled [source registry](docs/npa_registry.md) and [screen-lock interpretation](docs/npa_workstation_lock.md) document the mapping. Recheck current wording and effective dates before a real banking deployment. Automatic access to current Adilet text was unavailable during this release check, so this release does not claim a new legal verification.

The 30-minute automatic-lock requirement does **not** establish a violation in a short clip. The service does not establish permissions, money ownership, complete seal/bag inspection, finished transactions, accounting correctness, document return or banknote authenticity. Invisible conditions must be checked by a person. An unlocalized screen/door/safe region or unreadable answer appears as a coverage warning.

## Verification and measured limits

```bash
.venv/bin/python -m pytest -q
node --check app/static/app.js
.venv/bin/python -m tools.audit_release
```

**Release checks:** 27 Python tests passed. The real local HTTP smoke test completed a positive clip in 67.47 s and a negative clip in 17.22 s, with valid result/evidence contracts. Browser checks passed on desktop and mobile using explicitly synthetic API fixtures. These two smoke clips do not constitute a new accuracy evaluation.

Unit/contract tests use synthetic videos and worker fixtures. They check auth, the positive/negative API shape, JPEG evidence, upload limits (including chunked bodies), persisted jobs, restart recovery, exclusive process ownership, worker timeouts, source mapping and local key setup. They do not prove model accuracy. GitHub Actions repeats these checks and validates deployment configuration; a configured workflow is not a claim that its remote run has already passed.

For browser checks against a running local server:

```bash
npm ci
npx playwright install chromium
npm run test:ui
```

The browser script defaults to `http://127.0.0.1:8004`; use `UI_TEST_BASE=http://127.0.0.1:8003 npm run test:ui` for the standard local launcher. It intercepts analysis responses with synthetic fixtures and does not upload footage to the models. To use a second local server port, add `--port 8004` to `tools.start_local_service`. The browser script saves private local screenshots under `local-evaluation/ui/`.

After starting the real service, run an actual upload/poll check using footage you are permitted to use:

```bash
.venv/bin/python -m tools.smoke_http your-video.mov \
  --output local-evaluation/my-smoke.json
```

For a deployed service add `--base https://YOUR_DOMAIN`. Configure the same private `API_KEY` locally. The tool verifies real HTTP responses, decoded JPEGs, source fields and completion status, and writes metrics without evidence to an ignored file.

The prior integrated Mac run processed **40 unique organizer videos**, with **32/40 correct verdicts (80%)**, **14 true positives**, **7 missed positives**, **18 true negatives**, and **1 false alarm**. Positive recall was **66.7%**. Median processing was **20.88 seconds**, maximum **120.71 seconds**. It produced 17 events and 33 decodable JPEGs. These are development regression results: the imported classifiers were trained on organizer footage, so this is not an independent or unseen-camera accuracy estimate. Temporal accuracy and type accuracy have not been quantified against independent ground truth. Linux/CUDA has not been benchmarked here. See the [evaluation checklist](docs/JURY_REQUIREMENTS.md) for remaining acceptance work.

Known failures include missed events, false detections, occlusion, reflections, small objects, camera changes, uncertain roles, unreadable screens and incomplete rule coverage. The system requires human review and further bank validation before operational use.

## Data handling and operations

Uploaded videos are private runtime files with random names. They are deleted after processing or restart recovery. Intermediate feature/state caches are deleted after each run; stale caches from a terminated worker expire by TTL. Results contain evidence and are protected by the key until expiry. Browser previews stay on the user's device, and downloaded reports remain there until the user removes them. No uploaded video enters a training pipeline.

Security controls include constant-time key comparison, auth before parsing protected uploads, request/file limits, host allowlisting, no-store responses, a restrictive browser policy, no external frontend assets, private file modes, a single-process lease and worker timeouts. The deployment adds HTTPS, an unprivileged read-only app container, capped logs, and an internal inference network. A shared jury key is a hackathon access mechanism; a bank deployment needs separate access roles, incident handling and an approved retention policy.

## Attribution and hackathon eligibility

The distribution includes a modified MIT-licensed third-party inference implementation and two trained state classifiers. The original license, source commit, original and distribution hashes and changes are in [third_party](third_party/THIRD_PARTY_NOTICE.md). RT-DETRv2, OWLv2, DINOv2 and Qwen model weights are downloaded separately under the verified model-card licenses.

FAQ 24 permits commercially usable open-source components, while FAQ 35 prohibits ready-made solutions. MIT licensing permits reuse but does **not** establish eligibility under FAQ 35. Organizer approval remains unresolved. Do not claim full competition compliance until that question is settled.

## Submission checklist

- Provision a public GPU host and DNS name, then complete [deployment](docs/DEPLOYMENT.md).
- Verify UI, API, HTTPS certificate, readiness and upload/poll from outside the host network.
- Run unseen-angle positive/negative tests and record failures and latency.
- Pass the five-minute end-to-end limit on the actual host under expected load.
- Generate the private handoff with `tools.prepare_jury_access`; share it only with the jury.
- Resolve third-party implementation reuse eligibility with the organizers.
- Keep all footage, labels, keys, results and private handoff files out of Git.
