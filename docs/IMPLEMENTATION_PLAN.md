# ForteBank implementation plan

The supplied plan is valid. Keep its focus on event detection, localization, evidence, and verified Kazakhstan rules. Begin with an offline baseline and local annotation; do not present an unclassified anomaly as a legally identified action.

## Case requirements

- One MOV upload through a browser; progress and two possible verdicts.
- Every flagged event needs a type, exact timestamp, visible-action explanation, 1–3 JPEG evidence frames, and a relevant public Kazakhstan source.
- Jury endpoints: POST /api/v1/analyze, multipart file, X-API-Key; GET /api/v1/jobs/{job_id}; statuses processing, done, failed.
- Completed jobs use verdict violation/no_violation and evidence_frames objects containing timestamp_sec and image_base64.
- Return within five minutes; public web and API URLs plus a jury key required.
- Offline inference with commercially usable open-source components. No audio, identity recognition, or cloud AI processing of videos, frames, or descriptions.
- Supplied and test videos stay private and are used only within the hackathon. Never commit recordings, evidence, or dataset-derived artifacts to the public repository.

## Implemented foundation

- Private dataset audit, normalized Latin/Cyrillic IDs, SHA-256 grouping, metadata validation.
- Local review screen with timestamp seeking and saved event annotation.
- Cheap trainable spatial appearance/motion baseline. Positive training frames are restricted to ±2 seconds around supplied timestamps; frames outside these intervals remain unlabeled. Negative videos provide normal examples.
- Stratified video-hash holdout; duplicates stay in a single group. The saved model uses only the training fold. Fixed threshold 0.65 is not tuned on holdout results.
- Browser upload, persistent SQLite job state, one local inference process, bounded admission, key authentication, evidence generation and upload cleanup.
- Local-only annotation endpoints disabled by default for deployment.

## Next work in priority order

1. Review all positive clips locally, including both X-4/X-47 timestamps. Define categories that are visually distinguishable. Compare difficult negatives. Current annotation editor stores one interval per recording; extend it to multiple events before exhaustive annotation.
2. Add complete typed intervals, ambiguous examples, verified source title/clause/URL, and a description of what video can and cannot establish. Confirm mappings directly on NBRK and Adilet. No source has been legally verified in this starter.
3. Implement a typed training path using reviewed annotations. Current baseline intentionally uses only supplied binary labels and does not consume the saved action annotations.
4. Compare an appropriately licensed local visual encoder and temporal action classifier against this baseline. Add temporal context, region/object interactions, and train-fold-only threshold selection.
5. Evaluate action type, event precision/recall, localization, multiple events, and evidence quality. Add recording-session/scenario grouping where identifiable and a separate camera-angle test. Existing hash grouping prevents exact duplicate leakage only.
6. Replace generic descriptions with verified visible-action explanations and reviewed rule cards. Keep unsupported categories explicitly unclassified.
7. Benchmark end-to-end runtime on target hardware, package weights, verify offline operation, deploy one service instance behind HTTPS and request-size limits, and test externally with the jury key.
8. Prepare architecture, model/component licenses, supported types, known errors, API example, demo script, and final submission URLs.

## Submission blockers

This is a development baseline, not a completed detector. No verified violation taxonomy, rule catalog, unseen-angle validation, external deployment, or production accuracy claim is provided. A no_violation result means the baseline found no event above its threshold; it does not establish procedural compliance. One evidence peak per contiguous predicted segment is supported, but this is not a learned temporal action model.

Never raise a development benchmark score by hard-coding file names, hashes, supplied verdicts, or timestamps into the inference path. Hashes exist only for splitting and auditing.
