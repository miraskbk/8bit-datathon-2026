# Public deployment and jury access

No public host/domain is configured for this release. These steps prepare a Linux/NVIDIA deployment with Caddy HTTPS. The team must execute and verify them on its host. The Docker build, CUDA backend and public TLS path have not been exercised on the development Mac.

## Host requirements

- Public Linux host with an NVIDIA GPU and enough memory for RT-DETRv2, OWLv2, DINOv2 and Qwen3-VL-4B together. Start planning at 16 GB VRAM, then measure actual use and adjust. This is an estimate.
- Compatible NVIDIA driver, Docker Engine, Docker Compose with GPU support, and NVIDIA Container Toolkit. See [Docker GPU configuration](https://docs.docker.com/compose/how-tos/gpu-support/) and [NVIDIA installation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
- A real DNS hostname pointing to the host. Permit inbound TCP 80/443 and UDP 443 if HTTP/3 is wanted. Keep app port 8000 private. Restrict SSH to administrators.
- Disk for Python/CUDA dependencies, model weights, image layers and temporary runtime data. Plan more space than the 10 GB model-only minimum.
- Internet during image creation for packages and weights, plus the gateway's certificate issuance/renewal. The inference container has no external network at runtime.

## Configure private access

```bash
git clone https://github.com/miraskbk/8bit-datathon-2026.git
cd 8bit-datathon-2026
uv sync --locked --extra dev
.venv/bin/python -m tools.setup_local --backend transformers
```

Edit the generated `.env` privately. Keep the generated `API_KEY`; it must have at least 32 characters. Set these additional values, replacing the example with your actual DNS name:

```dotenv
DEMO_DOMAIN=review.your-domain.example
ALLOWED_HOSTS=["review.your-domain.example","127.0.0.1","localhost"]
PRELOAD_MODEL=true
MAX_PENDING_JOBS=1
ANALYSIS_TIMEOUT_SECONDS=270
```

The example domain is a placeholder. Do not publish your `.env` or key. Compose overrides the backend/model/job paths to the correct in-container locations. The local `runtime/jury-access.txt` initially describes loopback access; generate the final public handoff only after deployment.

## Build and start

```bash
docker compose config --quiet
docker compose build app
docker compose run --rm --no-deps gateway caddy validate \
  --config /etc/caddy/Caddyfile --adapter caddyfile
docker compose up -d
docker compose ps
docker compose logs --tail=80 app
```

The build downloads model weights without any private recording present and pins Python dependencies using `uv.lock`. Startup preloads the models. The gateway waits for the app's readiness health check before accepting traffic. A failed startup is a deployment failure, not a clean video result. If loading needs more than the health-check startup window, measure the reason and adjust the window without weakening the jury processing deadline.

The app runs as UID/GID 10001 with a read-only filesystem, writable private runtime volume and temporary storage. Its Docker network is `internal: true`. The gateway belongs to that network and a public network, terminates HTTPS and forwards to the app. Only the gateway publishes ports. See [Compose network isolation](https://docs.docker.com/reference/compose-file/networks/) and [Caddy body limits](https://caddyserver.com/docs/caddyfile/directives/request_body).

Do not use multiple app replicas or Uvicorn workers with the same runtime volume. To scale, each instance needs its own jobs and a job-aware routing design; that design is outside this release.

## Verify from another network

Use the real public hostname from a laptop or phone outside the host network. Confirm valid HTTPS without certificate warnings.

1. Open `/` and `/docs`. Ensure static assets, file selection and status text work.
2. Confirm `/ready` returns HTTP 200 and `/health` reports loaded models.
3. Confirm a missing/wrong `X-API-Key` returns 401 on both protected endpoints.
4. Upload at least one permitted positive and one negative video. Poll each to completion. Inspect the actual verdict, event type, exact timestamp, complete JPEG frames and linked rule.
5. Test at least one new camera angle. Record false alarms, missed events and localization errors; do not infer accuracy from synthetic contract tests.
6. Measure **total upload plus processing plus polling latency** against the five-minute limit. A 270-second worker limit cannot guarantee slow network transfers finish within five minutes.
7. Confirm concurrent capacity rejection returns 429 with `Retry-After: 15`.
8. Keep the service awake and reachable for the judging period. Restart once and confirm readiness and interrupted-job recovery.

You can run the real HTTP checker from a checkout with the same private key:

```bash
.venv/bin/python -m tools.smoke_http your-positive.mov your-negative.mov \
  --base https://YOUR_DOMAIN --output local-evaluation/public-smoke.json
.venv/bin/python -m tools.prepare_jury_access --url https://YOUR_DOMAIN
```

The handoff tool verifies public routes and key enforcement, then writes **`runtime/jury-submission.md`** with the UI URL, API base, instructions, readiness URL and key. The file has mode `0600` and is Git-ignored. Share its contents only with the jury through the official submission channel. This tool does not replace a real video test. Do not send footage, frames or model-generated descriptions to any external AI service while diagnosing deployment.

After public verification, replace the README's pending-demo notice with your real HTTPS UI link. Do not insert the key there.

## Monitoring and recovery

```bash
docker compose ps
docker compose logs --tail=100 app
docker compose logs --tail=100 gateway
```

Logs rotate at 10 MB with three files per service. Access logging is disabled for the app/gateway recipe. Runtime errors use job IDs and stay in host logs; client responses do not disclose tracebacks or local filesystem paths. A failed worker is stopped, and the next job triggers model reload. `/ready` stays 503 until models load again. A completed job survives API restart until TTL expiry; an interrupted job is marked failed and must be re-uploaded.

For a service problem:

```bash
docker compose restart app
docker compose ps
```

A container's `unhealthy` state requires investigation; Docker's restart policy alone does not restart an unhealthy but running process. Use host monitoring during judging. Check weights, GPU memory, volume permissions, `.env` and the hostname allowlist. Do not resolve an error by disabling mandatory model components or returning a negative verdict.

## Updates, rollback and cleanup

Record `git rev-parse HEAD` and the deployed image ID before an update. Keep a previous image tag so rollback does not require an online rebuild. Stop acceptance during updates, wait for the running job to finish where practical, rebuild, restart and repeat the external smoke test. Rotate the API key in `.env`, recreate the app and privately issue the new handoff if a key is exposed.

Original uploads are deleted after processing or restart recovery. Results/evidence expire at the configured TTL with up to a 60-second cleanup interval; killed-worker caches expire too. Browser downloads and operator backups require separate deletion. Stop the service and remove the private runtime volume after the authorized retention period. `docker compose down` retains volumes; `docker compose down -v` also destroys results and Caddy certificate state, so use it only when intentional.

A bank production rollout additionally needs its approved identity/access controls, retention policy, monitoring, security review and independent accuracy/robustness acceptance. This hackathon candidate does not establish those approvals.
