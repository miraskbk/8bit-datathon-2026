# Forte Review — 8bit Datathon 2026

An offline video-review prototype for the ForteBank case: upload a MOV, poll a job, and inspect possible events with timestamps and JPEG evidence. Includes a private dataset audit and local annotation screen.

**Status: experimental baseline.** The first model learns binary weak labels using coarse visual appearance and motion. Action classification and verified regulatory explanations remain to be built. Do not submit this baseline as a completed compliance detector. See [implementation plan](docs/IMPLEMENTATION_PLAN.md).

## Run locally

Python 3.14 is tested. From this directory:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
.venv/bin/python scripts/audit.py /absolute/path/to/open
PYTHONPATH=. .venv/bin/python scripts/train.py
```

The audit reads `open_labels.xlsx` and `videos/` without copying or uploading videos. Training writes private `models/baseline.joblib` and `data/evaluation.json`. No pretrained weights or network services are required for this baseline. Do not load untrusted joblib files.

Create `.env` from `.env.example` and set a long random `FORTE_API_KEY`. For team annotation on your own machine set `FORTE_ENABLE_REVIEW=1`. Then:

```sh
.venv/bin/uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000 --workers 1
```

Open http://127.0.0.1:8000 and enter the API key. The dataset review tab plays recordings locally and saves an event interval, action category, observation, and optional verified source. Saved annotations are a preparation tool; the binary training script does not yet consume them.

## Jury API

```sh
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "X-API-Key: YOUR_KEY" -F "file=@/absolute/path/video.mov"
curl http://127.0.0.1:8000/api/v1/jobs/JOB_ID \
  -H "X-API-Key: YOUR_KEY"
```

Upload returns HTTP 202 and `job_id`. Poll status `processing`, `done`, or `failed`. Completed results contain `verdict` and `violations`; each violation includes `type`, `timecode_sec`, `description`, and 1–3 evidence objects with `timestamp_sec` and `image_base64`. Current type is `possible_violation_unclassified`; rule is null until a reviewed mapping exists. Wrong keys return 401. Missing model returns 503. Unsupported extension returns 415, oversized files 413, busy service 429. Invalid video becomes a failed job, never a clean verdict.

## Data and deployment

- Data, SQLite jobs, model weights, evaluation, annotations, and recordings are ignored by Git. Private paths stay in the local manifest.
- Uploads are deleted after processing; interrupted uploads are removed at restart. Completed results contain evidence in SQLite. Rows older than 24 hours are removed on restart. Delete local data at the end of the hackathon according to organizer instructions.
- Run exactly one web worker/instance: the queue is in-process. SQLite persists results, not the queue; interrupted jobs are marked failed at restart. Only one analysis is admitted at a time so waiting work cannot overrun the jury deadline.
- Decoding has a 180-second cooperative time budget and accepts videos up to 180 seconds and 100 MB. Native decoder hangs are not forcibly killed in this prototype; the five-minute end-to-end requirement still needs hardware testing.
- Public deployment must disable `FORTE_ENABLE_REVIEW`, set a strong key, use HTTPS and proxy upload-size limits. Do not expose private dataset endpoints. The web UI asks the user to enter the key; no key is embedded in public assets.
- Dockerfile packages local weights if present. Build after training, or mount a trusted artifact at `FORTE_MODEL_PATH`. No videos are copied into the image. Container writable data should be mounted at `/service/data`. No external deployment is configured yet.
- All application inference code is local. Dependency installation needs internet initially. Prove offline operation on the final deployment before submission.

## Validation

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

First local benchmark: 1/5 positive videos detected (20% recall), 3/5 negative videos falsely flagged (60% false-positive rate). This is insufficient for submission. A real held-out MOV completed the API upload/poll/evidence flow in 3.1 seconds on the development machine; this is one smoke test, not a worst-case runtime guarantee.

The training script evaluates a fixed, stratified 25% holdout of unique hashes. Exact duplicate recordings never cross folds. Reported numbers are from a small development split and do not establish generalization, action classification, or different-camera performance. Do not tune on this holdout repeatedly.

## Architecture

Browser → FastAPI → bounded queue → local process → OpenCV features + ExtraTrees → timestamped JPEG evidence → SQLite result → browser / jury API.

No cloud AI, audio analysis, or face identification. Dependencies include FastAPI (MIT), OpenCV (Apache 2.0), NumPy and scikit-learn (BSD), and openpyxl (MIT); verify all resolved component licenses before commercial submission. The repository itself has no license grant yet; the team should choose one.
