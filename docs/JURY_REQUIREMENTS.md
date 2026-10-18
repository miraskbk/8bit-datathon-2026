# Jury requirements and release evidence

This matrix follows the supplied ForteBank Datathon 26 brief, sections 4–10 and FAQ. The source Word file contains organizer material and is deliberately excluded from the public release. API/interface checks are not substitutes for detection accuracy or organizer approval.

## Required behavior

| Requirement | Implementation / evidence | Release status |
| --- | --- | --- |
| Web upload without manual analysis commands | `/`, MOV drag/drop, API call and polling inside UI | Implemented; synthetic browser and API checks |
| Processing status | Loading/validation/analysis states, elapsed time, job ID and status retry | Implemented |
| Exactly two completed verdicts | `violation` / `no_violation`; failed jobs have no verdict | Contract tested |
| Several events per video | Result list and independent event cards | Implemented |
| Type, timestamp, concise visible explanation | Every event includes mandatory jury fields | Positive API contract tested |
| Evidence | 1–3 full JPEGs in base64, timestamps, complete-frame UI and download | Contract tested; prior real regression decoded 33 frames |
| Rule and source | Document, point/section and Adilet URL on every event | Enabled rules have source-mapping tests |
| No invisible conclusions | Qualified descriptions, coverage warnings, human-review notice | Implemented; legal applicability still requires review |
| Local inference | Pinned local weights, offline loaders, no cloud AI client | Implemented; Compose isolates inference network |
| Transferability | Separate weight setup, offline runtime, Docker recipe | Mac tested; Docker/CUDA host verification pending |
| Visual only | No audio input or biometric face identification | Implemented |
| `POST /api/v1/analyze` | MOV in multipart `file`, 202 and `job_id` | Contract tested |
| `GET /api/v1/jobs/{job_id}` | `processing` / `done` / `failed`, completed result schema | Contract tested |
| API-key access | `X-API-Key`, 401 before protected upload parsing | Tested for missing/wrong keys |
| Five-minute maximum | 270-second supervised worker deadline, bounded admission, client timeout | Watchdog tested; public end-to-end host test pending |
| About 29 MB MOV, up to 145-second source videos | Defaults 35 MiB and 180 seconds | Byte/metadata boundary tests |
| Public URL and private key handoff | HTTPS Compose/Caddy recipe and private handoff tool | **Pending: host, DNS, external verification** |
| Instructions, architecture, model list | README, deployment and integration documents | Included |
| Event types, sources, limitations | README coverage table and source registries | Included |
| Test footage stays private and is never training input | Ignored runtime, upload deletion, no training endpoint | Implemented; operator must respect dataset policy |
| Commercially usable components (FAQ 24) | MIT CashGuard attribution, Apache-2.0 download checks | Licensing recorded |
| No ready-made solutions (FAQ 35) | Full CashGuard reuse disclosed | **Organizer eligibility approval unresolved** |

## Scoring criteria

| Criterion | Points | Evidence available | Remaining validation |
| --- | --- | --- | --- |
| Detection quality | 25 | 32/40 source-set verdicts correct, TP14/FN7/FP1/TN18 | Independent holdout and unseen-angle recall/false alarms |
| Localization | 15 | Per-event second timestamps, 1–3 JPEGs, prior JPEG decoding checks | Timestamp error and frame relevance against independent labels |
| Event classification | 15 | Explicit visible event types with cautious wording | Independently labeled per-type accuracy |
| Rule justification | 15 | Kazakhstan source mapping, indirect matches disclosed | Current act wording/effective dates and applicability review |
| Robustness | 10 | Limits, failure states, restart recovery, worker isolation | New viewpoints, lighting, occlusion and unknown events |
| Product readiness | 10 | UI, API guide, readiness, file/error handling, private access | Real public-host browser and end-to-end acceptance |
| Technical solution/locality | 10 | Local model architecture, pinned weights, offline loading | CUDA/Docker execution and egress verification on host |

No total jury score is claimed. Contract tests do not establish quality under these criteria. The 80% source-set figure is a development regression, and the imported classifiers trained on organizer footage. It is not an independent accuracy claim. Positive recall is 14/21 (66.7%), so missed events remain a material limitation.

## Submission gates

The source code can be reviewed and tested now. To claim submission readiness the team must also complete public deployment, verify the exact jury API remotely with real permitted videos within five minutes, assess unseen viewpoints, and resolve FAQ 35. To claim operational bank production readiness it must additionally complete the bank's acceptance, security and data-governance process.
