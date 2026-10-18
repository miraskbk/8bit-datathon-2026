# Third-party implementation notice

This distribution includes a modified MIT-licensed third-party vision implementation
and two trained state classifiers. Copyright (c) 2026 AliNurym. The original
copyright and permission notice are reproduced unchanged in
`VISION_PIPELINE_LICENSE`.

Source base commit: `7836a1aace1c2148b08228158f2aca5bf488f8a0`.
The imported working tree also included local MLX backend support. Original source
hashes and current distribution hashes are recorded in `pipeline-provenance.json`.

Included components: modules under `app/visioncore/`, feature extraction,
`artifacts/safe_clf.joblib`, `artifacts/money_clf.joblib`, and the regulatory
source registries under `docs/npa_*.md`.

Modifications include package/resource/environment-variable names, offline model
loading, local model paths, private cache handling, and conversion to 8bit's
API/UI schema. The API adds supervised deadlines, bounded capacity, persisted
results and cleanup. Renaming components does not change their third-party origin.

The hackathon permits commercially usable open-source components in FAQ 24 but
prohibits ready-made solutions in FAQ 35. Licensing does not establish competition
eligibility. Organizer clarification for reuse remains necessary.
