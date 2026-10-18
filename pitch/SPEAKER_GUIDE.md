# Five-minute pitch script

Present slides 1–8 in 300 seconds. Slides 9–10 support the two-minute Q&A. The main script contains 620 words. Rehearse with a timer and keep the ending slide visible for questions.

## 1. 8bit cash-discipline video review

Time: 20 seconds.

We built 8bit to help a reviewer inspect possible cash-discipline violations in video. The reviewer receives the moment, evidence and a regulatory reference in one place. All models execute inside our service. The output supports a human decision.

## 2. Reviewer workflow

Time: 35 seconds.

The browser accepts MOV video, starts analysis and polls the same API the jury will use. It shows processing state and the job ID. Each flag includes a type, a timestamp, one to three complete evidence frames, and a rule reference. Clicking the timestamp seeks the preview. The screenshot shows the actual empty interface. It contains no organizer recording. A no-violation result has an empty event list, while a failed analysis has no verdict.

## 3. Local model architecture

Time: 45 seconds.

The API validates and stores a private job, then a supervised process handles inference. RT-DETRv2 and OWLv2 find people, objects and scene regions. DINOv2 features and small state classifiers support safe and cash checks. Local Qwen answers a limited set of screen and door questions. Rules combine these observations over time and select evidence. The tested Mac uses Qwen3-VL-8B in MLX four-bit format. The Linux recipe uses Qwen3-VL-4B with Transformers, so it needs its own benchmark. No video, frame or generated description goes to a cloud AI API.

## 4. Regulatory reasoning

Time: 40 seconds.

We separate an observation from facts the video cannot establish. A person behind the desk does not prove they lack permission. A short bag handoff does not prove there was no inspection outside the recording. An active screen in a short clip does not prove a breach of a thirty-minute automatic-lock requirement. We return the Kazakhstan source and disclose indirect relationships. The source snapshots and interpretation are documented, but current wording and applicability need review before bank deployment.

## 5. Development results

Time: 50 seconds.

All forty unique source videos completed. Thirty-two verdicts were correct: fourteen true positives and eighteen true negatives. We missed seven positives and produced one false alarm. That gives eighty percent video accuracy and sixty-six point seven percent positive recall. Median processing took twenty point eight eight seconds, with a maximum of one hundred twenty point seven one. These are development regression results. The classifiers trained on organizer footage, so we do not present this as unseen-camera accuracy. Timestamp and per-type accuracy still need independent labels. Improving missed events on a new camera is a central next step.

## 6. Jury access and API

Time: 40 seconds.

The required API is implemented exactly as two steps. The jury uploads a MOV file in the multipart file field, receives a job ID, and polls processing, done or failed. Both endpoints require X-API-Key. The completed response includes the mandatory fields, plus regulatory references and coverage metadata. The guide is served locally without a CDN dependency. We provide a Caddy HTTPS and GPU deployment recipe and a private handoff generator. We have not provisioned a public host yet, so remote jury access is a remaining submission gate.

## 7. Reliability and data handling

Time: 35 seconds.

We checked twenty-seven Python tests and the desktop and mobile browser flow with synthetic fixtures. A real local positive and negative HTTP smoke test also completed with valid evidence contracts. Those checks establish integration behavior, not independent detection quality. We enforce upload limits, bounded admission and a supervised deadline. Original recordings are deleted after processing, results expire by retention time, and model failures never turn into no-violation results. The deployment adds HTTPS and an isolated inference network. It still needs validation on the real public host.

## 8. Public pilot and acceptance plan

Time: 35 seconds.

The next step is a controlled pilot using permitted clips from an independent camera view. We want to measure recall, false alarms, timestamp error and whether the evidence actually supports the observation. Before judging, we must provision the public GPU service and privately hand over the URL and key. Pilot acceptance also requires independently reviewed event labels and regulatory interpretation. We can demonstrate the local product today, with those limits stated clearly.

## 9. Event coverage appendix

Use this slide for questions about event coverage. Every category describes a visible indicator. Some regulatory relationships are indirect and require context. G drinking and L screen-state matches are particularly indirect. The production pipeline does not verify accounting correctness, document return or banknote authenticity. The type names use cautious wording to avoid treating hidden facts as established.

## 10. Jury Q&A appendix

Keep answers concrete. The twenty-seven tests check software contracts and boundaries, not unseen accuracy. The source-set study includes seven missed positives, so no claim of negligible misses is supported. Public deployment, CUDA timings and independent camera-angle validation are pending. A bank production deployment requires its own governance, security and independent acceptance process.
