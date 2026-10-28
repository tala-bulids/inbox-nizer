# Phase 2 — reproducible classification research

28 October 2026; development branch `codex/ai-showcase-phase1`, starting at
`906e228d20b1e43956b9bff874b9e380be76987f`. This phase never changes the serving
model, website, Google configuration or database. Experiment outputs are research
evidence, not release approval. The original V10 gate is unchanged.

## Dataset and rights decision

The admitted source is [imnim/multiclass-email-classification](https://huggingface.co/datasets/imnim/multiclass-email-classification/tree/e95090f0bb6dae0b05c9cd6db314dcae1d40db3f),
pinned to `e95090f0bb6dae0b05c9cd6db314dcae1d40db3f`. Its publisher declares MIT
in the dataset card and supplies `dataset_creation.py`, which uses GPT-3.5-turbo
to generate synthetic messages and labels. That code is inspected, **never executed**;
no paid API is used. No row-level generation logs exist in the source, so this
does not establish the origin or correctness of each individual example.

MIT ordinarily permits use, modification and redistribution subject to retaining
copyright/permission notices ([license terms](https://opensource.org/license/mit)).
This repository has a license declaration rather than a separate detailed rights
chain or privacy assurance. The decision here is local research under the publisher's
declared grant. **Do not redistribute source text, fitted vocabularies, private
checkpoints or row-level predictions.** Only code and aggregate results are committed.
Publisher attribution, pinned URLs and source hashes remain in the dataset card.
Downloading a public dataset does not establish that all names in it are fictional.

Potential contact information is screened before training. Email addresses, URLs
and long number sequences are redacted locally; names and semantic personal details
can remain. No personal Gmail data is accessed. No personal-mail approval is implied.

The original 2,105 rows yield 2,103 usable examples. Two rows in one conflicting
exact duplicate group are quarantined. There are 131 near-duplicate pairs, including
38 with differing labels; their connected template groups stay together rather
than silently rewriting annotations. Three rows change under contact redaction.
Source rows have no sender/thread metadata. Sender-domain grouping is supported
when provided, but only content/template grouping is possible for this source.
There are 1,995 groups; train/validation/reserved test counts are 1,679/215/209.
Class and split distributions are in `evidence/dataset-card.json`.

All 2,103 usable rows are English by a script heuristic, not human language review.
There are **no admitted Arabic classification labels or action/deadline labels**.
No translation or synthetic Arabic supplement is presented as independent gold.
Task/action training is therefore **NOT EXECUTED**; existing rule extraction stays.

Other sources were considered without changing the target task: UCI Spambase is
licensed but provides spam features rather than this ten-label text taxonomy;
Enron-derived sets raise real-mail privacy and lineage concerns; the Arabic email
literature located during this review did not establish an accessible, licensed,
compatible ten-category dataset. This is a bounded source review, not a claim that
no suitable Arabic dataset exists. Independent bilingual annotation remains needed.

## Labels and preprocessing

Labels are the existing multilabel contract. These working descriptions explain
the application taxonomy; they do not replace the publisher's annotations:

| Label | Intended meaning |
|---|---|
| Business | General professional/work correspondence |
| Customer Support | Requests or responses about service/account problems |
| Events & Invitations | Invitations and event participation |
| Finance & Bills | Invoices, payments and financial correspondence |
| Job Application | Recruitment and employment applications |
| Newsletters | Recurring informational digests |
| Personal | Personal/social correspondence |
| Promotions | Commercial offers and advertising |
| Reminders | Follow-up/time-sensitive reminder messages |
| Travel & Bookings | Travel arrangements and reservations |

Use the existing `quality.dataset` cleaner/grouping logic with NFC normalization,
whitespace normalization and explicit contact redaction. Preprocessing is shared
across all three comparison candidates. Raw row indices and SHA-256 provenance are
retained in ignored local split files. Exact normalized duplicates collapse; their
source references are retained. Conflicting exact labels are quarantined.
Transitive character-template cosine >=0.9 groups and available sender-domain
groups cannot cross splits. Vocabulary/IDF and class weights fit on training only.
Near-template discovery sees corpus text solely for leakage-resistant partitioning;
it is not a prediction feature fit. Group splits are seeded, not class-stratified.

## Frozen experiment scope

`ml_phase2/config.json` was fixed before measured runs. One fit per new candidate;
no hyperparameter search, relabelling, retries until a desired score or final-test
selection is performed.

- **A:** word/character TF-IDF, balanced one-vs-rest logistic regression, C=1.
  Sparse interpretable features, CPU inference. The fitted vocabulary stays local.
- **B:** historical `checkpoint-3159`, verified against the existing source-file
  hashes. Inference only, sigmoid/top-one semantics and the original token limit.
  It may have trained on these public examples. Its validation score is explicitly
  contaminated and **excluded from model selection**.
- **C:** [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small),
  MIT-declared pretrained encoder, snapshot `614241f622f53c4eeff9890bdc4f31cfecc418b3`,
  frozen CPU features plus the same balanced linear head. The publisher recommends
  the `query: ` prefix for classification; embeddings are normalized. This reuses
  an available multilingual model instead of downloading a larger candidate.
  **Training its linear head is not transformer fine-tuning or proof of Arabic accuracy.**

Research selection is validation top-one macro-F1, then accuracy, then lower p95
serial latency. Only A/C are eligible. Language coverage and resource constraints
remain adoption gates. Any selected research artifact is not a production winner.

The historical 32/100 difficult-development result, macro-F1 0.2839, English 20/56
and Arabic-heavy 1/11 remain disclosed in [V03/V10 evidence](../release/V03_V10_EVIDENCE.md).
Those are consumed diagnostic slices, not representative accuracy. A high score
on this synthetic public corpus neither contradicts nor repairs that evidence.

## Evaluation integrity

Development loaders read only frozen `train.json` and `validation.json` and verify
their hashes; they never open `test.json`. Test allocation requires initial data
preparation, but there are **no test predictions or test performance results**.
This public corpus was used in older experiments: reserving a new partition does
not make it a new untouched release holdout. Obtain a separately sourced final
holdout before invoking the existing `quality.classifier_release` final workflow.

Top-one accuracy accepts any annotated label. Macro/weighted F1 and per-class
precision/recall compare the one predicted label with all reference positives;
they are not ordinary mutually exclusive multiclass F1. Confusion rows distribute
one example's weight over its gold labels. ECE, correctness Brier score, confidence
bins and confident errors are measured; raw sigmoid scores remain uncalibrated.
Language slices report `unavailable`, not zero performance, when unsupported.
Validation is consumed by selection and cannot be advertised as test accuracy.

Warm latency includes preprocessing and single-message inference on 30 validation
messages, after one warmup. RSS after and Windows process peak working set include
load/training overhead. Measurements are workstation observations, not isolated
inference allocation, target-host capacity or guarantees. Candidate runs execute
in separate processes to avoid retaining the previous candidate's model.

## Fine-tuning recipe

`python -m ml_phase2.finetune` provides an offline Hugging Face/PyTorch recipe for
locally provisioned DistilBERT snapshots. It fixes Python/NumPy/Torch/CUDA seeds,
uses strict deterministic algorithms, trains the last two encoder layers and head,
fits capped positive-class weights only on training, logs weighted training and
validation BCE each epoch, and selects checkpoints on validation macro-F1/accuracy.
Three epochs maximum, patience two, batch four, 256 tokens, AdamW 2e-5, weight decay
0.01, gradient clipping 1.0. Each improved epoch has a versioned checkpoint; output
directories cannot overwrite existing models. Dataset/config/base/artifact hashes
and library versions are recorded. The recipe never opens final test data.

The available workstation has CPU-only Torch and initially about 1.8 GiB free RAM.
Real transformer fine-tuning is **NOT EXECUTED** here; the CLI requires at least
3 GiB available RAM before starting. This is a conservative preflight floor, not
a guarantee that every model fits. A deterministic tiny random-model unit test
exercises optimizer updates, losses and checkpoint reload; it is **not** a trained
portfolio checkpoint. Use an authorized local GPU/notebook for a separately
recorded real fine-tuning run after data and resource prerequisites are satisfied.

## Reproduction

Use Python 3.11 and `python -m pip install -r ml_phase2/requirements.txt` in a research
environment, never the production web service. CPU Torch is sufficient for A/B/C;
use the appropriate authorized PyTorch build for a future GPU run. No production
environment file, database or Google credentials are needed.

```sh
python -m ml_phase2.fetch --output results/phase2-source
python -m ml_phase2.data --source-dir results/phase2-source --output results/phase2-data
python -m ml_phase2.run --candidate A --data results/phase2-data --output results/phase2-A
python -m ml_phase2.run --candidate B --data results/phase2-data --model-path /absolute/path/to/checkpoint-3159 --output results/phase2-B
python -m ml_phase2.run --candidate C --data results/phase2-data --output results/phase2-C
python -m ml_phase2.report --runs results/phase2-A results/phase2-B results/phase2-C --data results/phase2-data --output results/phase2-aggregate
python -m pytest --confcutdir=ml_phase2 ml_phase2/tests -q
```

Provision B privately and C's pinned Hugging Face snapshot separately; neither is
downloaded by the runners. Set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`,
`TOKENIZERS_PARALLELISM=false`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` for runs.
Fetch must be run before offline flags if the host's environment applies them to
network tools. All output directories must be new; do not remove old evidence.
Only the allowlisted aggregate report directory is eligible for source control.

For the prepared, **not executed** real fine-tuning workflow:

```sh
python -m ml_phase2.finetune --data results/phase2-data --base-model /absolute/path/to/distilbert-snapshot --output results/phase2-finetuned-v1
```

Do not use `joblib.load` on untrusted artifacts. New research candidates remain
under ignored `results/`, separate from `CLASSIFIER_ONNX_PATH` and serving hashes.
No ONNX re-export is justified merely to publish a training result. If a future
transformer passes selection and the unchanged gate, reuse
`deploy/export_classifier_onnx.py` into a new directory and verify framework/export
parity before provisioning. Existing ONNX weights are untouched.

## Required evidence still missing

Independent reviewed Arabic/English classification data; licensed action labels
before action training; a truly untouched representative final holdout; calibrated
confidence validated independently; and target-host capacity for any adopted model.
The original coverage, accuracy, macro-F1, per-class/Finance, calibration and
language-gap thresholds remain unchanged. No website metric or production model
is updated by this phase. Stop here; no deployment or automatic next phase.

## Execution and verification evidence

Two classifier fits actually completed (A and C); B ran inference only. See the
[model card](MODEL_CARD.md), [generated comparison](evidence/experiment-comparison.json)
and [qualitative error analysis](ERROR_ANALYSIS.md). Selected A remains local.
No final-test, Arabic or action-detection performance is reported.

Final checks: **13 pipeline tests passed**, **5 existing training/data tests passed**,
and **18 showcase tests passed** (one existing Starlette/httpx deprecation warning).
The pipeline tests include split/provenance preservation, sender/template isolation,
changed-data rejection, forbidden test-file reads, calibration/metric definitions,
legacy exclusion and deterministic tiny-model training/checkpoint reload. Frontend
checks were not repeated because Phase 2 changes no frontend code. Exact commands,
execution status and non-executed work are in [verification.json](evidence/verification.json).
