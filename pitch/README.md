# 8bit pitch

[Download the editable PowerPoint](8bit-pitch-revised.pptx). Open it in PowerPoint, Keynote or another compatible viewer. The deck contains eight slides for the five-minute pitch, plus two Q&A appendices. Speaker notes are embedded in every slide. [The speaker guide](SPEAKER_GUIDE.md) provides the same main script with timing. The script is timed for five minutes, leaving room for pauses.

## Running order

| Slides | Subject | Time |
| --- | --- | --- |
| 1 | Product and reviewer purpose | 20 s |
| 2 | Actual upload interface and checkable output | 35 s |
| 3 | Local model architecture | 45 s |
| 4 | Visible observations and regulatory limits | 40 s |
| 5 | Development accuracy, misses and timing | 50 s |
| 6 | Jury API and pending public access | 40 s |
| 7 | Reliability, test evidence and retention | 35 s |
| 8 | Public pilot and acceptance plan | 35 s |
| 9–10 | Coverage details and likely jury questions | Q&A, up to 2 min |

The deck uses actual empty UI screenshots, editable text/tables and an editable accuracy chart. It contains no organizer footage, evidence from real videos, labels by filename, private paths or API keys. Source citations are included in relevant speaker notes.

## Before pitching

- Rehearse slides 1–8 within five minutes. Use slide 8 for the closing and slides 9–10 only if useful during questions.
- Verify the displayed claims still match [the evaluation record](../docs/EVALUATION.md). Source-set development accuracy is 80%, with seven missed positives and 66.7% positive recall. It does not establish performance on an unseen camera.
- Keep public-host and independent-validation limits visible until those checks are complete. The release does not claim an already deployed or approved service.
- If showing the app, preload models and test one permitted clip in advance. Keep private keys out of screen sharing. Do not add private organizer frames to this public deck.
- A live upload takes time. If the jury requests a demonstration within the five-minute pitch, shorten the workflow/API commentary rather than adding a full live wait to the script. A previously completed local result may be shown only if its provenance and permissions are clear.
- Present the result as support for human review. Do not claim that video establishes permissions, transaction completion or accounting correctness.

## Main answers to prepare

**Accuracy:** Forty development clips completed with TP14/FN7/FP1/TN18. Independent camera-angle, event-type and timestamp validation remain pending.

**Locality:** All model inference runs locally in the service. Initial setup downloads weights only. Runtime never sends footage, frames or generated descriptions to cloud AI.

**Deployment:** The API and deployment recipe exist. The team still needs its public GPU host, DNS, external HTTPS/upload verification and private jury handoff.

**Operational banking use:** Further independent validation, approved access controls, monitoring, retention and security review are required.
