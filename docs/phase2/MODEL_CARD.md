# Model card — Phase 2 sparse research candidate A

Version: `phase2-A`, 28 October 2026. **Research selection only; production approval: NO.**
This artifact is not deployed or substituted for the existing ONNX classifier.

## Identity and intended use

Word/character TF-IDF with ten independent balanced logistic-regression heads.
Training seed 42, fixed C=1, liblinear, 1,000 iteration cap, 8,000 word features
and 16,000 character features maximum. Vocabulary and IDF fit on training only.
Model: ignored `results/phase2-A/candidate.joblib`.
SHA-256: `ad110b70dae9b9875e37ca43103519e23ff4afcb79219ded99ca02d38c8ce11d`.
The artifact contains a fitted vocabulary and must remain local, as must C's head.
The exact dependency versions and source/split hashes are in
[experiment-comparison.json](evidence/experiment-comparison.json).

Intended use is a reproducible, interpretable English research baseline for the
existing ten-category email domain. It is not approved for mailbox automation,
financial decisions, calibrated certainty, Arabic classification or public serving.
It has no task/deadline detector and no generative capability.

## Actual experiment results

These are **215-example English validation diagnostics**, not final-test accuracy.
Reference labels are the publisher's synthetic-data annotations. Model selection
uses validation, so these scores cannot serve as independent acceptance evidence.

| Candidate | Actual training in Phase 2 | Top-one accuracy | Macro-F1 | Weighted-F1 | Warm p95 ms | Peak process MiB |
|---|---|---:|---:|---:|---:|---:|
| A: TF-IDF + linear | Linear heads fitted | 0.883721 | 0.704303 | 0.642159 | 9.65 | 199.94 |
| B: checkpoint-3159 | None; existing model evaluated | 0.934884 | 0.726048 | 0.696192 | 153.56 | 633.09 |
| C: frozen E5 + linear | Linear heads fitted; encoder unchanged | 0.837209 | 0.659110 | 0.604709 | 222.22 | 915.46 |

B is excluded from selection: the original training partition is unknown and may
include these examples. This table does **not** establish a fair B-vs-A ranking.
Among eligible A/C, A has stronger measured validation F1 and lower latency/memory.
C's multilingual pretraining does not establish Arabic email classification quality;
there are zero admitted Arabic labels. No claim of a larger model being better is made.

Macro/weighted F1 use the project's top-one versus multilabel reference definition,
described in [the experiment methodology](README.md). Memory is measured process
peak working set including load/training overhead, not a hosting minimum. Latency
uses 30 warmed serial validation inputs. No Render benchmark was run.

## Calibration, errors and limitations

A's raw independent scores are uncalibrated. Validation ECE is 0.053855 and
correctness Brier score is 0.100006; 20 incorrect predictions have scores >=0.8.
These diagnostics do not justify displaying scores as reliable probabilities.
No calibration transform was fit on validation and then evaluated on that same
validation set. Independent calibration and evaluation data are still needed.

The dataset is template-heavy, imbalanced, weakly annotated, English-only and
lacks sender/thread metadata. Duplicates are grouped, but undetected paraphrases
and historical exposure remain limitations. Review the
[error analysis](ERROR_ANALYSIS.md), per-class CSVs and fractional confusion matrices.
No row-level data or model artifacts are redistributed.

Historical V10 evidence remains **FAIL**: 32/100 on difficult consumed development
examples is not representative accuracy. A's result neither repairs that failure
nor meets the unchanged representative bilingual release requirements.

## Test, training and export status

- Reserved public test: **NOT EVALUATED** in Phase 2. The corpus is historically
  exposed, so this partition is not a newly untouched release holdout.
- Independent representative final test: **UNAVAILABLE**.
- Arabic validation/test: **UNAVAILABLE**, not zero accuracy.
- Real transformer fine-tuning: **NOT EXECUTED**; reproducible HF/PyTorch pipeline
  is validated with tiny random-model tests only.
- Task/action training: **NOT EXECUTED**, no compatible annotated action dataset.
- New ONNX export: **NOT EXECUTED**. No new transformer was selected; converting
  the sparse research model is not needed for this experiment. Existing source and
  ONNX artifacts retain their identities and are not overwritten.
- Deployment: **NOT PERFORMED**.

Before adoption: obtain licensed representative bilingual data, human-review
annotations, freeze an independent final holdout, complete calibrated evaluation
and all unchanged quality gates, then verify the selected serving artifact's parity
and actual target-host resource limits. Do not automatically run another search.
