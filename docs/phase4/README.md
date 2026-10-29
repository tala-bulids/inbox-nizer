# Phase 4 — interactive AI portfolio

29 October 2026. Development branch: `codex/ai-showcase-phase1`, based on
Phase 3 commit `96fc1c0bb10c66aacbc8e94f61de22aa00ad11e8`. Local implementation;
not a deployment or production model approval. The intended public URL remains
`https://inbox-nizer-beta.onrender.com`. No new website was created.

## Functional inventory

- **Ask Mail:** editable questions, bilingual suggestions, real E5 retrieval,
  explicitly extractive answers, inline citations and source cards, insufficient
  evidence, loading, input-limit and busy/error recovery.
- **Smart Tasks:** per-email or collection-wide extraction, deadlines, missing or
  ambiguous date states, responsible person, conditional/cancelled requests and
  exact evidence linked to the original fictional email. Completion is unknown.
- **Email Collection:** 24 CC0 authored bilingual emails, local text filtering,
  sender/date/body inspection, persistent source selection in the URL and refresh.
  This is sample data, not personal mail or a representative quality benchmark.
- **Model Lab:** three measured experiments, model/artifact identity, selection
  rationale, dataset/splits/class distribution, executed hyperparameters, saved
  final losses, per-class metrics, fractional confusion matrices, calibration,
  paraphrased errors, language gaps and historical quality failures. The
  reproduction link serves the committed research instructions locally.
- **Playground:** editable short text, genuine inference using selected research
  candidate A, raw score (not correctness probability), model version, actual
  server processing time and extractive summary. No simulated retraining.

Shared React windows, navigation styling, typography, AskComposer, locale provider
and RTL/LTR behavior are reused. The old `/intelligence` URL opens Model Lab.
The private Gmail application, ONNX/DistilBERT and optional Qwen code remain intact.
The historical `/showcase/analyze` endpoint still identifies its historical model;
the new UI explicitly calls `/showcase/predict` for candidate A. No model artifact
has been overwritten and no RAG/task algorithm has changed after Phase 3 evaluation.

## Actual Model Lab evidence

All numeric displays are read from committed Phase 2/3 JSON, not invented fixtures.

| Candidate | English validation top-1 accuracy | Macro F1 | Weighted F1 | Selection |
| --- | ---: | ---: | ---: | --- |
| A: TF-IDF + balanced OVR logistic regression | 0.883721 | 0.704303 | 0.642159 | Selected research candidate |
| B: historical DistilBERT checkpoint-3159 | 0.934884 | 0.726048 | 0.696192 | Excluded: unknown prior training overlap |
| C: frozen multilingual E5 + fitted linear head | 0.837209 | 0.659110 | 0.604709 | Lower measured F1, slower and larger than A |

These are **215 consumed English validation examples**, not final test accuracy.
Accuracy accepts any gold label; per-class F1 compares one prediction to all gold
labels. Fractional confusion counts allocate 1/number-of-gold-labels per row.
A's final train/validation binary log losses are 0.142303 / 0.189434; C's are
0.283911 / 0.293809. Epoch loss curves are **Not available**, because no epoch history
was recorded for the one-shot linear fit. No new transformer fine-tuning occurred.
Selected-model Arabic and final test metrics are **Not evaluated**. The historical
32/100 difficult development result, English 20/56 and Arabic-heavy 1/11 are retained
as failed, consumed diagnostics. No threshold or production approval was changed.

Sources: [experiment comparison](../phase2/evidence/experiment-comparison.json),
[dataset card](../phase2/evidence/dataset-card.json), [model card](../phase2/MODEL_CARD.md),
[Phase 3 evaluation](../phase3/README.md). Phase 3's two evidence failures and the
lack of independently authored/human-reviewed evaluation remain explicit.

## Privacy and bounded operation

The showcase app imports no production Gmail/DB entry point and requires no login.
Client API calls omit credentials, use no-store and never persist input in browser
storage. There is no analytics or third-party inference API. Questions/pasted text
are request-local; application code does not log, cache or write them or train on
them. Only the authored corpus index and loaded model objects are cached.

Limits: 300 subject characters, 6,000 body characters, 1,000 question characters,
24,000 request bytes, one inference at a time and a rolling **30 attempts/minute per
process** shared by inference endpoints. The budget stores timestamps only, no IPs
or text. 429 includes Retry-After. Validation/model failures omit submitted content.
These safeguards are not a distributed or per-user abuse service, and they cannot
preempt a stuck native inference. Use one worker and qualify resource/time limits
before public activation; proxy/provider body logging must remain disabled.

The classifier verifies the SHA-256 of the **same opened file handle** before
joblib deserialization and requires the recorded sklearn version. Missing/mismatched
artifacts fail closed with 503. Never substitute an arbitrary downloaded pickle.

## Reproduce locally

Use the existing Python 3.11 environment with `ml_phase2/requirements.txt` and the
recorded Phase 3 runtime. The selected classifier requires scikit-learn 1.9.1,
joblib 1.6.0, threadpoolctl 3.7.0 and numpy 2.4.6. Ask uses the existing pinned
Torch 2.13.0 / Transformers 5.14.1 / SentenceTransformers 5.7.0 stack. Exact prior
encoder/runtime evidence is in [runtime.json](../phase3/runtime.json).

Provision the existing artifact at `results/phase2-A/candidate.joblib`, or set
`SHOWCASE_CLASSIFIER_PATH` to its absolute local path. Expected SHA-256:
`ad110b70dae9b9875e37ca43103519e23ff4afcb79219ded99ca02d38c8ce11d`.
It is deliberately untracked. Reproduction/retraining must create a separate
artifact; do not silently replace this recorded identity. Provision the verified
`intfloat/multilingual-e5-small` snapshot
`614241f622f53c4eeff9890bdc4f31cfecc418b3` in the local cache before serving.
No request downloads a missing model. ONNX/Qwen are not needed by the new public UI.

PowerShell, in this checkout, using an activated prepared environment:

```powershell
# frontend directory
npm ci
npm run build:showcase
# repository root; no production .env or Gmail/DB credentials
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:TOKENIZERS_PARALLELISM='false'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
python -m uvicorn showcase.api:application --factory --host 127.0.0.1 --port 4181 --workers 1 --no-access-log
```

Verification, using writable unique `--basetemp` paths on Windows where needed:

```sh
python -m pytest --confcutdir=showcase showcase/tests -q
# frontend
npm test
npm run typecheck
npm run lint
npm run build:showcase
node scripts/check-phase4.mjs
```

The real classifier test runs when the exact local artifact is present; otherwise
it explicitly skips. UI unit mocks verify behavior only. `check-phase4.mjs` uses
real local model responses with installed Edge/Playwright, never request mocks.

## Verification and screenshots

Final frontend: **185 tests passed in 12 files**, typecheck/lint/showcase build
passed. Final focused UI: **12 passed**. All **44 backend showcase test cases**
were verified: the final full run had 43 passes and one 60-second real-classifier
subprocess timeout; the unchanged isolated retry passed in 22.83 seconds. The prior
full run passed 44/44. No real-model test was skipped. Existing Starlette/httpx and
Rollup annotation warnings remain. A build attempt failed with ENOSPC; the retry
passed when disk space became available, without deleting user data.

A final cold Ask browser attempt exceeded 120 seconds. The process remained healthy,
finished initialization and passed the complete warm desktop/mobile flow. This is
**not** a cold-start readiness pass and must not be hidden behind warm screenshots.
Target-host initialization, timeout/admission and memory qualification remain open.

See [browser-verification.json](browser-verification.json) and
[verification.json](verification.json) for exact executed checks and source hashes.
The browser flow covers original and new questions, abstention, Arabic questions,
tasks/evidence, source navigation, live classification, experiment switching,
confusion matrices, actual saved losses/metrics, RTL/LTR, mobile layout and refresh.

Screenshots are actual local production-build UI with authored `example.invalid`
data and real inference. No private mailbox, credentials or training-source rows
appear. They are interaction evidence, **not quality benchmark evidence**.

- [Desktop Model Lab](screenshots/1440-lab-en.png)
- [Desktop Ask Mail](screenshots/1440-ask-en.png)
- [Mobile live prediction](screenshots/390-prediction-en.png)
- [Mobile Arabic task evidence](screenshots/390-tasks-ar.png)
- [Arabic evaluation](screenshots/1440-evaluation-ar.png)

## Remaining hosting requirements

**Render Free remains NO-GO for the present learned retrieval runtime.** Phase 3
measured an E5-only process peak of 880.27 MiB against the previously verified
512 MB allocation. Adding the sparse classifier does not establish a fit. Separate
process peaks are not a combined-service measurement. No Linux/Render capacity
claim or new paid hosting recommendation is made here.

Before activation at the existing URL: approve a hosting/resource decision, package
the verified artifacts and dependencies offline, test combined cold/warm/maximum
input/concurrent load on the actual allocation, configure the isolated entry point
without production credentials or migrations, and verify proxy logging/security.
Public deployment is separate and requires approval. This phase neither deploys nor
opens another implementation phase. Independent bilingual classification/QA/task
quality evidence is still required before claiming production model quality.
