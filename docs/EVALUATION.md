# Evaluation record

The results below summarize the integrated Mac pipeline's prior development regression. No recordings, labels by filename, evidence images or source paths are published in this record.

| Measure | Result |
| --- | --- |
| Unique source videos | 40 |
| Completed / failed | 40 / 0 |
| True positive / false negative | 14 / 7 |
| True negative / false positive | 18 / 1 |
| Correct video verdicts | 32 / 40 (80%) |
| Positive recall | 14 / 21 (66.7%) |
| Positive precision | 14 / 15 (93.3%) |
| Negative false-alarm rate | 1 / 19 (5.3%) |
| Median / maximum processing | 20.88 s / 120.71 s |
| Events / decodable JPEG evidence | 17 / 33 |

The classifier weights were trained on organizer footage. These are source-set regression numbers, **not independent holdout accuracy**. Do not claim that 80% establishes performance on unseen cameras. There were seven missed positive videos. The hackathon expects strong detection, localization, event classification and robustness, so this is an explicit remaining quality risk.

The backend is local MLX Qwen3-VL-8B 4-bit on a Mac with 24 GB unified memory. The Transformers Qwen3-VL-4B Linux backend uses different model weights and has no measured result here. The prior source videos were deduplicated before evaluation. Timing excludes provisioning/model download; public upload latency requires a separate deployment measurement.

Timestamp error, relevance of every selected frame and per-type accuracy have not been independently quantified. Changes in camera geometry, reflections, occlusion, unreadable screens and object scale need separate evaluation. Model/API contract tests and a small smoke test cannot replace that evaluation.

The required next record is an independent set of permitted new clips, ideally from a new angle, with video verdicts, event labels, timestamps and frame relevance reviewed by humans. Report confusion counts, timing percentiles, missed/extra events, timestamp error and completion failures. Keep private video-level records outside Git.

## Release verification

The production candidate passed 27 Python tests and desktop/mobile browser contract checks using synthetic API fixtures. A new real local TCP upload/poll smoke test completed one previously evaluated positive clip in 67.47 s (one event, valid evidence) and one previously evaluated negative clip in 17.22 s (no events). Both returned the expected verdict and passed schema/JPEG checks. This is a two-clip integration check, not a repeated 40-video study or an independent accuracy estimate. The host must still be tested remotely after deployment.
