# 8bit vision architecture

The default pipeline is now `visioncore`. It invokes the complete upstream
inference graph from 8bit's web upload and jury API: RT-DETRv2 + OWLv2 extraction,
scene and anonymous person tracks, DINOv2-based safe/cash classifiers, selected
local Qwen screen/door questions, upstream rules, and annotated evidence frames.
This testing distribution contains only the integrated production pipeline.

## Preserved behavior

Detection frequencies, scene geometry, tracking, thresholds, state classifiers,
query planning, rules, timestamps, deduplication and evidence selection come from
the copied working tree. The local MLX backend uses separately downloaded
8B 4-bit Qwen weights. Upstream's default Transformers backend uses a 4B model;
results can differ by backend and hardware. The original project's reported
accuracy and NVIDIA timings must not be presented as measured 8bit results.

## Integration changes

- Package imports and all resource paths point into this repository; no sibling
  checkout or external script is required at runtime.
- The MIT notice, both trained classifiers and source registries are included.
- All model loads use local files. Initial setup downloads weights only, before
  processing private recordings.
- The adapter adds 8bit's `rule` object to each event, preserving the jury schema
  and existing evidence-card interface. It also exposes runtime coverage metadata.
- Required model components must load. Runtime model errors become `failed`;
  absent scene regions are disclosed as limited coverage, not invisible checks.
- The API's supervised worker enforces the deadline, kills a stalled process,
  records private results atomically and removes uploaded videos. The vision pipeline's
  intermediate caches are private and deleted after each job; stale caches left
  by a killed worker expire with the configured TTL.
- Separate model processes avoid mixing PyAV and OpenCV video libraries in the
  vision worker. The parent validates uploads using PyAV; the worker uses
  upstream OpenCV decoding.

## Rules and limitations

Enabled upstream rules include unattended valuables, an open safe after departure,
cash on a desk when another visitor enters, crowding/position behind a cashier,
short visible bag handoff, personal items/drinking, an open door after entry and
an unlocked workstation after departure. Some are indirect review indicators:
video does not establish access permissions, money ownership, complete bag
inspection or whether a transaction finished. The adapter explicitly qualifies
those conclusions. Document return and banknote-authenticity verification are
not established by the production pipeline.

The source normative registries are in `npa_registry.md` and
`npa_workstation_lock.md`. The screen-lock source is indirect: the 30-minute
inactivity requirement does not establish a breach in a short clip.

## Competition eligibility

FAQ 35 bans ready-made solutions. MIT licensing permits code reuse but does not establish
hackathon eligibility. Organizer clearance remains necessary to claim compliance
with that clause. See `third_party/THIRD_PARTY_NOTICE.md` for provenance and changes.

## Verification

Run unit/contract tests with `.venv/bin/python -m pytest -q`. For a local
upload/poll check, use `.venv/bin/python -m tools.smoke_http your-video.mov
--output local-evaluation/my-smoke.json` after starting the service. Do not call this unseen accuracy: the imported classifiers were
trained on organizer footage. Record verdict confusion counts, timestamp errors,
frame validity, processing failures and end-to-end latency on the deployment host.
