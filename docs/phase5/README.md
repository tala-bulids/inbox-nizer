# Phase 5 — measured release candidate, deployment not authorized

29 October 2026. Branch: `codex/ai-showcase-phase1`. Application baseline:
`8a0ee5a1aca4c75c53f3348ff2f9681fbb0f10ca`. No Render configuration, production
mailbox, database, credential or model artifact was changed. **PUBLIC AI SHOWCASE:
NO-GO.** The intended URL remains https://inbox-nizer-beta.onrender.com; the AI
showcase is not deployed there. No additional website was created.

## What actually ran

Three fresh Windows CPU processes served the real React build and FastAPI over
loopback HTTP. Each loaded selected classifier A and its own E5 encoder, indexed
all 80 chunks from the 24 authored emails, answered real questions, extracted tasks,
classified new text, exercised the 512-token encoder boundary and handled four
concurrent requests. No model output was mocked. Models were already on disk;
OS disk cache was not controlled and Render's 0.1 CPU allocation was not emulated.
These are process peak-working-set measurements, not Linux cgroup memory proofs.

| Encoder | Peak MiB | First Ask ms | First classifier ms | Warm Ask p50 / p95 ms | Warm classifier p95 ms |
|---|---:|---:|---:|---:|---:|
| Existing Torch E5 | 918.21 | 17974.32 | 236.84 | 20.73 / 20.89 | 10.51 |
| Existing FP32 ONNX E5 | 940.32 | 3194.61 | 2367.88 | 14.08 / 14.71 | 9.67 |
| Existing INT8 ONNX E5 | 398.00 | 2297.46 | 2977.19 | 9.91 / 10.85 | 9.75 |

Cold HTTP listener readiness took 1.56–2.10 seconds in the diagnostic harness,
**before models were initialized**. First Ask includes the index build. The actual
release factory now initializes both models before binding and exposes readiness
only afterward; do not present the harness's listener time as model readiness.
Warm percentiles above use only five repetitions, not an SLA/load-test estimate.
Full 512-token inference: 277.22 / 474.25 / 408.46 ms respectively. The index's
float32 payload is 122,880 bytes, excluding Python object overhead included in
process memory. Selected classifier: 2,552,375 bytes; INT8 graph: 118,065,353 bytes;
compact tokenizer: 5,069,051 bytes. No Qwen model is loaded.

Four simultaneous requests produced 200/429 only; one inference runs at a time.
Torch admitted one request, rejected three; ONNX admitted two sequentially and
rejected two. This is bounded admission evidence, not a throughput guarantee.
Tasks p50: 12.54 / 14.17 / 13.96 ms; frontend p50: 1.99 / 2.05 / 1.91 ms.
All three processes confirmed no `database` or `gmail_sync` module imported.
ONNX probes also confirmed no Torch/Transformers/SentenceTransformers imports.

## Parity and the optimization decision

Original cached E5 files match every pinned SHA-256 in the Phase 2 manifest.
The existing FP32 export has identical query token IDs and top-ten rankings on
all 20 questions. Query/component error <=1.12e-7; document error <=1.27e-7.
This is strong numerical parity on these inputs, not a signed original export log.

INT8 token IDs match; minimum query cosine is 0.99137, document cosine 0.98935.
Citation **sets**, statuses and Recall@5 are unchanged. Ranking is not unchanged:
19/20 top-ten orders differ. MRR falls 0.76190 -> 0.72024 and nDCG@5 falls
0.69897 -> 0.68668. No post-evaluation tuning, retraining or threshold reduction
was performed. The ONNX adapter remains **offline qualification code only**.
It is not selected by the normal app or release factory and is not silently
promoted over the original encoder. A small measured footprint alone is not
permission to claim preserved model quality or target-host qualification.

| Frozen development evidence | Original / FP32 | INT8 |
|---|---:|---:|
| English Recall@5 | 0.78571 | 0.78571 |
| Arabic Recall@5 | 0.73810 | 0.73810 |
| Overall Recall@5 | 0.76190 | 0.76190 |
| Correct evidence sets | 18/20 | 18/20 |
| Citation precision | 0.96875 | 0.96875 |
| Missing-evidence abstention | 6/6 | 6/6 |

These are the same consumed, same-author fixtures, not an independent held-out
acceptance set. Tasks match 12 labelled actions on 16 messages; all four negative
messages are English. Arabic false-positive rate is not evaluated. The retained
q09 current-day filtering error and q10 mixed positive/negative-line error remain.
See [machine-readable comparison](capacity-comparison.json) for per-language
ranking, task counts, case-level citation IDs, latency samples and receipt hashes.
Raw vectors remain ignored under `results/`; no training data or weights are shipped.

## Serving architecture and safety changes

React -> same-origin FastAPI -> hash-verified sparse classifier A and pinned
pretrained E5 -> bounded in-memory corpus index -> deterministic evidence composition.
Tasks/deadlines are deterministic extraction. No LLM generation is claimed.
The historical fine-tuned DistilBERT code and Gmail application remain preserved.

`showcase.release_app:application` is a separate, reviewed factory. It refuses
mailbox-related environment configuration before importing the engine, verifies
E5 source files, pins its revision, verifies A through the existing loader and
warms both models before `/api/health/ready` can return 200. Failures are sanitized.
It rejects `/showcase/analyze` before invoking the historical model; local
`showcase.api` behavior remains unchanged. The release factory retains Torch E5
and therefore is **not eligible for the current Free allocation**.

The optional `EMBEDDING_REVISION` leaves existing local/full defaults unchanged.
The direct dependency proposal excludes Gmail libraries, SQL drivers, Alembic,
training datasets and GGUF. Linux clean-install qualification is still required.
No request downloads weights, stores pasted text, trains, or sends text to an API.
Existing 24k body-byte, 1000 question-character, 6000 body-character, single-inference
and 30-attempt/minute limits remain. Provider request-body logging must separately
be disabled/verified; local tests cannot prove provider policy.

## Research identity and honest portfolio scope

A: word/character TF-IDF plus ten balanced logistic heads, fitted with seed 42.
Artifact SHA-256: `ad110b70dae9b9875e37ca43103519e23ff4afcb79219ded99ca02d38c8ce11d`.
Selected from actual A/C validation; historical DistilBERT B is excluded due to
unknown overlap. No transformer was newly fine-tuned. E5 is unchanged pretrained
`intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`.
[Runtime identities and artifact hashes](runtime-identity.json).

Training corpus: publisher-MIT `imnim/multiclass-email-classification`, pinned
`e95090f0bb6dae0b05c9cd6db314dcae1d40db3f`, 2103 usable English rows,
1679 train / 215 validation / 209 reserved test. Publisher supplies synthetic
generation code but not per-row origin evidence. Raw rows and fitted vocabulary
artifacts remain private. Validation accuracy 0.883721, macro-F1 0.704303,
weighted-F1 0.642159; selected-model Arabic/final-test results **not evaluated**.
Historical 32/100 difficult development result remains FAIL, not accuracy.
[Dataset, experiment methodology and reproduction](../phase2/README.md).
E5's pinned publisher model card declares MIT. The public application corpus is
24 independently authored fictional records under CC0, exclusively example.invalid
senders; it contains no personal Gmail messages.

## Verification and publication

See `verification.json` and `browser-verification.json` for final checks. Browser
verification uses real models in fresh local Edge contexts at 1440 and 390 pixels,
Arabic/English, original/new questions, missing evidence, tasks/citations, classification,
Model Lab, language switching and deep-link refresh. This is **local** evidence.
Phase 4's committed screenshots still accurately show the same UI; fresh Phase 5
screenshots are kept locally under `results/phase5-browser/screenshots`.

No live acceptance was attempted against the old Free service: waking a suspended
instance could execute its existing migration-on-start command. Render inspection
found no available memory/latency series and no matching application error logs;
neither absence is a health/capacity pass. [Exact transition and approval boundary](../../deploy/AI_SHOWCASE_RELEASE.md).

README live-launch claims and GitHub Homepage are intentionally unchanged until
public acceptance passes. Safe CV wording now:

> Built a bilingual email intelligence portfolio with multilingual E5 retrieval,
> source-cited extractive answers and evidence-linked task extraction. Developed
> reproducible grouped-data experiments comparing TF-IDF linear classification,
> a historical DistilBERT model and frozen multilingual embeddings; documented
> validation results, leakage risks, model limitations and measured serving costs.

## Reproduce the release measurements

Use the existing prepared Python 3.11 environment, Phase 2 requirements and
provisioned model artifacts. ONNX probes additionally need ONNX Runtime 1.31.0.
Build `frontend` with `npm ci` and `npm run build:showcase`. Use fresh receipt paths:

```sh
python -m showcase.release_probe --encoder torch --output results/new-torch.json
python -m showcase.release_probe --encoder onnx-fp32 --artifacts /approved/local/embedding --output results/new-fp32.json
python -m showcase.release_probe --encoder onnx-int8 --artifacts /approved/local/embedding --output results/new-int8.json
python -m showcase.release_report results/new-torch.json results/new-fp32.json results/new-int8.json --output results/new-comparison.json
```

Run sequentially. The diagnostic server is loopback-only and must never be deployed.
All receipt outputs refuse overwrite. This harness removes DB/Google/OAuth settings
from its child environment and does not import the private app or load `.env`.
The actual release factory refuses those settings instead of silently ignoring them.
A repeated measurement is not a fresh holdout and does not erase earlier failures.

## Final GitHub release record

Published normally to `codex/ai-showcase-phase1`; no force push or main merge.
Release preparation: `1b6176dc695d7cd8eec9c2ea7fd230ff8f10eb43`.
Test-fixture isolation correction and verified code/test HEAD:
`d7d5712dcb943b16c9900229352ad948f2d305eb`.
[GitHub run 40893033160](https://github.com/tala-bulids/inbox-nizer/actions/runs/40893033160)
completed successfully: 1,450 backend tests passed, 6 skipped, 2 subtests passed;
isolated showcase 57 passed/1 private-artifact skip; ML pipeline 13 passed;
quality unittest 11 run/1 skipped; frontend 185 passed; pip check, typecheck,
lint, API contract and all three frontend builds passed. Local showcase ran
58/58 including the actual private classifier. Initial CI exposed two new tests
being overridden by the legacy fake-encoder fixture; the correction is test-only.

The final documentation-only follow-up records these results with `[skip ci]`;
it does not change the application or tests and does not claim another CI run.
The green SHA above identifies exactly what CI exercised. No Render service,
private database, credentials, model weights or public Homepage were modified.
**PUBLIC AI SHOWCASE remains NO-GO** until the artifact/compute/approved-transition
and target-host acceptance boundaries in the runbook are resolved.
