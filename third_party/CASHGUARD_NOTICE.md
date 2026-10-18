# CashGuard integration

This project includes MIT-licensed CashGuard code and trained safe/cash classifiers
from the local `cashguard-datathon26` checkout. Upstream repository:
https://github.com/AliNurym/cashguard-datathon26.
Base commit: `7836a1aace1c2148b08228158f2aca5bf488f8a0`.
The copied working tree also contains its local MLX backend support.
The full license and copyright notice are in `CASHGUARD_LICENSE`.

Imported components: all modules under `app/cashguard/`, upstream feature
extraction, `artifacts/safe_clf.joblib`, `artifacts/money_clf.joblib`, and the
normative source registries under `docs/npa_*.md`.

Integration changes: package-relative imports and project paths, local-only model
loads, local VLM path selection, private feature caches, and adapter conversion to
8bit's authenticated API/UI schema. The source rules and thresholds are preserved.
8bit's own API supervises the worker, enforces deadlines/capacity, persists results,
cleans private files, and exposes coverage failures.

FAQ 35 of the hackathon brief prohibits ready-made solutions. This direct reuse
is disclosed and may affect eligibility; license permission does not resolve the
competition rule. Organizer clarification is required to resolve that competition rule.
