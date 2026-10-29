# Inbox-nizer — AI Engineering showcase specification

**Phase 4 update:** [Current interface, serving instructions and verification](phase4/README.md) supersede the Phase 1 navigation and public-classifier descriptions below. Primary navigation is Ask Mail / Smart Tasks / Email Collection / Model Lab. Model Lab performs genuine inference with the selected Phase 2 TF-IDF research artifact via `/showcase/predict`; the historical ONNX endpoint remains separately preserved. Public generation stays extractive. A shared 30-attempt/minute process budget supplements the single-inference lock. Epoch curves, Arabic classifier metrics and final test results remain unavailable. No deployment or production approval.

**Phase 3 update:** [The current Ask/task implementation and evaluation](phase3/README.md) supersede Phase 1's six-message collection and public optional-synthesis descriptions below. Public Ask is now explicitly extractive; historical Phase 1 evidence remains unchanged.

Phase 1, 28 October 2026. Development branch: `codex/ai-showcase-phase1`, based on
verified `693feb08f79a14aa019e576797fe93dfd8a4a619`. This product direction supersedes
the earlier Gmail-first release scope. This is a local functional foundation, not
a deployed release. Future public target remains **https://inbox-nizer-beta.onrender.com**.
No new public site, infrastructure, database or Google configuration was created.

## Final product scope

Inbox-nizer demonstrates AI engineering through email as a domain:

1. **Ask Mail:** real multilingual retrieval, literal source-grounded answers,
   explicit abstention, and optional clearly labelled local synthesis.
2. **Smart Tasks:** actual action/deadline extraction and original source evidence.
   Current extraction is rule-based; scores are rule strengths, not probabilities.
3. **Email Intelligence:** editable text, real classifier inference and extractive
   summaries. Predictions are experimental; they are not precomputed fixtures.
4. **Model Lab:** traceable model identity, training/evaluation methodology, actual
   recorded development results, bilingual slices and live prediction access.

The existing React theme, typography, window components and RTL/LTR behavior stay.
Gmail/OAuth, account ownership, PostgreSQL/pgvector and private RAG remain in source
as optional legacy functionality. They are not dependencies of the showcase entry
point. No original data, checkpoints, credentials, tests or history are removed.

## What will be trained, and what runs inference

- **Phase 1 trains nothing.** It preserves `app.py`, `evaluate.py`, classifier
  contracts, training reports and release evaluation tooling.
- A later explicitly authorized training phase may fine-tune DistilBERT for the
  existing ten-label email taxonomy. Freeze the dataset/splits, seeds, preprocessing,
  token limits, label mapping and artifact hashes, and compare with the current
  baseline. No model replacement, threshold relaxation or training is implicit here.
- The running classifier is the existing FP32 ONNX export of checkpoint-3159.
  Before first prediction the showcase checks config, tokenizer, graph and external
  weights against the committed V03 manifest. Wrong/missing artifacts fail closed.
  Serving preserves the existing sigmoid/top-one semantics.
- E5 is **pretrained multilingual-e5-small**, not a model trained by this project.
  It computes normalized passage/query embeddings on CPU using the existing module.
- Qwen3-0.6B GGUF is an **optional pretrained local generator**, not a fine-tuned
  project model. It is invoked only for requested synthesis when literal grounding
  cannot answer. Invalid citations or explicit abstention never become an answer.
- Summaries and tasks reuse existing extractive/rule algorithms. They are not
  presented as neural fine-tuning results.

### Quality honesty

V03 provenance and 111/111 Torch/ONNX parity remain established. V10 remains FAILED.
Model Lab reads the committed aggregate evidence, not a fabricated leaderboard:
100 consumed difficult-development examples, 32% top-one accuracy, macro-F1 0.2839;
English 20/56 and Arabic-heavy 1/11. These small heuristic language slices are not
representative generalization results. The baseline's original training split/report
is unavailable. See [the full experiment evidence](release/V03_V10_EVIDENCE.md).

The existing quality policy stays unchanged: at least 300 representative reviewed
examples, 20 per class, 50 per language, accuracy >=0.90, macro-F1 >=0.85, and the
existing per-class, Finance, calibration and language-gap conditions. A later
evaluation must use independent evidence, not the showcase corpus or consumed dev set.

## Dataset strategy

`showcase/collection.json` contains six newly authored, fictional emails: three
English and three Arabic, with workshop, application, billing, newsletter and project
contexts. Senders use `example.invalid`; no mailbox export is copied. Literal dates
and source texts allow reproducible functional checks. Corpus IDs are local showcase
identifiers and cannot address a private Gmail record.

This corpus is **interaction material only**, never a training/evaluation holdout.
Prediction inputs and questions are bounded, request-local and not written to disk,
cached as user data, or used for training. Visitors are asked to use fictional text.
Future datasets need provenance/license review, deduplication and group-disjoint
splits. Human-reviewed bilingual evaluation and untouched final holdout labels must
remain separate from model selection and UI examples. No private Gmail dataset may
be published or assumed available for this purpose.

## Reused components and minimal serving architecture

```text
Existing React/Vite UI, compiled in showcase mode
  -> same-origin /api/showcase/* (credentials omitted)
  -> showcase.api, independent FastAPI entry point
       -> authored immutable JSON collection
       -> existing ONNX classifier
       -> existing extractive summary / tasks / deadline modules
       -> existing E5 encoder -> small in-memory cosine index
       -> existing evidence selection / literal grounding
       -> optional existing Qwen provider / RAG prompt / citation validation
```

- `DesktopTopBar`, `RetroWindow`, `AskComposer`, `LocaleProvider`, `AppBoundary`,
  shared styles and React Router are reused. The private App/AuthProvider is not
  mounted in showcase mode. Ordinary and historical demo builds remain separate.
- `onnx_classifier`, `embedding_service`, `rag_evidence`, `rag_grounding`,
  `rag_prompt`, `local_llm`, `summarizer`, `task_extractor` and `deadline_extractor`
  are reused. Citation syntax validation was moved unchanged into a pure shared
  module; the legacy `rag_service._validate_citations` name remains compatible.
- The collection is small enough for an exact in-memory dot-product index. It
  contains one short passage per message; top three candidates feed the existing
  grounding logic. Corpus vectors are cached, user queries/results are not.
  No pgvector replacement is made to the legacy application.
- Literal answers quote source values with citations. Unsupported/ambiguous queries
  return `insufficient_evidence` and retrieved passages. Similarity is not confidence.
  Generated synthesis is marked `not_semantically_verified`: citation syntax does
  not prove factual entailment. The model never executes tools or instructions from
  retrieved mail.
- API request bodies are bounded to 24,000 bytes, question text to 1,000 characters,
  analysis body to 6,000 and subject to 300. Extra fields are rejected. A single
  inference admission lock returns 429/Retry-After for concurrent expensive work;
  no unbounded inference queue, worker or scheduler is added. Failures are sanitized
  and do not echo inputs. Responses use `no-store`.
- `showcase.api:application` reuses the existing same-origin static wrapper/security
  headers and refuses a build without `showcase-build.json`. It never imports the
  private backend `main`, connects to a database, or runs Alembic. There is no OAuth
  session dependency and no browser credential inclusion.

## Local setup and verification

Use Python 3.11 and Node 24, consistent with existing checks. Install the existing
locked frontend dependencies and Python requirements. On Linux choose CPU-only Torch
before installing `requirements.txt`; optional llama-cpp must be validated on that
host. `requirements-local.txt` is the existing Windows-only optional generator wheel.
Do not install that wheel on Linux. Training dependencies remain in the reused
requirements file; serving-package minimization is not part of this phase.

Provision the already identified ONNX export privately (four files matching
`docs/release/v03-v10-20261024.json`). Set `CLASSIFIER_ONNX_PATH` to its absolute
directory. Provision the E5 local Hugging Face cache explicitly; it is never
downloaded by a request. Its inspected snapshot is
`614241f622f53c4eeff9890bdc4f31cfecc418b3`. Optional Qwen uses the existing
checksum-verified `download_rag_model.py`; set `RAG_MODEL_PATH` to the existing file.
No credentials, model weights or Hugging Face cache belong in Git.

Set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `TOKENIZERS_PARALLELISM=false`,
`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`. Do not supply
DATABASE_URL, Google credentials, OAuth keys or the private service environment.

From the frontend directory:

```sh
npm ci
npm run build:showcase
```

From the repository root, start only the local server:

```sh
python -m uvicorn showcase.api:application --factory --host 127.0.0.1 --port 4181 --workers 1 --no-access-log
```

For development use `showcase.api:app` on port 8000 and `npm run dev:showcase`;
the existing Vite proxy strips `/api`. Do not run the Gmail `main:app` entry point
for this workflow. No migrations or account setup are required.

Verification commands:

```sh
python -m pytest --confcutdir=showcase showcase/tests -q
python -m showcase.verify_local --output results/new-real-model-smoke.json
```

The first command needs no PostgreSQL service or model files; it uses test doubles
only for inference boundary tests. The second explicitly runs real ONNX/E5 inference
on authored inputs. Existing legacy tests still use their guarded disposable test DB.
With the built local server running, execute `node scripts/check-showcase.mjs` from
frontend (Playwright with installed Edge). It uses real API/model responses and checks
1440/390px, Arabic/English, predictions, grounded answers, tasks, sources and refresh.

## Hardware and known risks

- Real local ONNX/E5 inference passed. The first English Ask included approximately
  15.35 seconds of cold E5 startup; warm Arabic Ask was approximately 0.020 seconds.
  These workstation smoke timings are not latency percentiles or Render guarantees.
- Earlier same-machine isolated model probes measured roughly 240 MiB classifier,
  866 MiB E5 and 911 MiB Qwen process peaks. Separate peaks must not be summed as
  a measured whole-server peak. Full combined target-host capacity is unverified.
- A single CPU worker on a **4 GB RAM / 2 CPU** host is a starting qualification
  candidate, not a certified minimum. Optional synthesis may need more headroom.
  Render Free's 512 MB allocation is not established as sufficient for this stack.
  No budget, paid plan, migration or provisioning is authorized by this document.
- Models must be provisioned before public activation. Missing artifacts yield 503,
  never fixed answers. Read-only browse/tasks still work without neural model files.
- The admission lock bounds concurrency but does not impose a hard inference timeout
  or prevent sustained public abuse. Target-host timeout, resource/admission and
  abuse-control acceptance are required before public deployment.
- Extraction has limited coverage. Generated answers can be wrong. No semantic
  correctness, bilingual classifier quality or broad QA quality pass is claimed.

## Precise acceptance criteria for later phases

These are gates, not authorization to begin the next phase:

1. Freeze licensed, deduplicated data/split manifests and a reproducible training
   recipe before any new DistilBERT run. Record hashes, seeds, library versions,
   resource cost and comparison against the current baseline.
2. Evaluate independently by language and class; retain failures and calibration
   evidence. Meet the unchanged classifier gate before claiming validated accuracy.
3. Add a frozen bilingual QA/extraction evaluation separate from the UI corpus:
   retrieval recall@k, literal-answer correctness, abstention, evidence/citation
   fidelity, negation, conflicting dates and prompt-injection cases. Choose and
   record thresholds before inspecting final labels; Phase 1 smoke is not that gate.
4. Run real neural and optional GGUF paths on the selected Linux allocation,
   including cold load, repeated maximum-length input and simultaneous visitors.
   Record process/whole-service peak RSS, p50/p95 latency, errors and 429 behavior.
   Demonstrate headroom and no OOM; approve actual hosting costs separately.
5. Verify no private backend import, Gmail/DB connection, user-input logging,
   cookies or synthetic-to-production writes in the actual hosted configuration.
   Recheck input limits, same-origin behavior, CSP, asset/deep-link handling and
   public abuse limits. Public showcase must receive no production secrets.
6. Only after explicit deployment approval, configure the existing original Render
   URL for this entry point with no automatic migrations. Preserve the old service
   configuration/data for a separately reviewed rollback. Do not create another
   public site or delete the existing historical demo.
7. Verify the deployed SHA and real anonymous flows at desktop/mobile sizes in both
   languages. Update GitHub presentation only after this hosted acceptance passes.

## Phase 1 evidence

- Isolated backend tests: **18 passed** without DB/Google configuration.
- Legacy shared RAG/grounding/local-provider regressions: **108 passed** using the
  existing guarded test database and fixtures; no production connection.
- Full frontend: **178 passed** before the final navigation regression was added.
  Final focused frontend suite: **6 passed**, including source-selection navigation.
  Typecheck, lint, unchanged API contract, standard build and showcase build passed.
- Actual local ONNX/E5 smoke: two language predictions returned; both literal
  workshop answers matched sources; unknown question abstained; six tasks extracted.
- Actual local production-build browser checks: 1440px and 390px, English/Arabic,
  real classification/Ask/tasks, Model Lab, source navigation and direct refresh;
  zero page errors, private API calls or cookies. Visual screenshots reviewed locally.
- Optional Qwen synthesis is wired and citation/abstention tested with unit doubles;
  its end-to-end showcase synthesis quality is **not verified** by the grounded smoke.
- No training, production migration, deployment, credential change or Phase 2 work.

Sanitized functional evidence is in [AI_SHOWCASE_PHASE1_EVIDENCE.json](AI_SHOWCASE_PHASE1_EVIDENCE.json).
