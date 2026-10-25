# V03 / V10 — classifier provenance and quality evidence

Verified 24 October 2026 against release code `1d37c4647f45bef5762b432be08f6a12f856f23f` (application candidate `b3225fa`). This is a focused follow-up, not a new model-selection campaign. Artifact paths below refer to the preserved original local workspace, not newly installed release assets.

## Verdict

- **V03 technical provenance: PASS.** The FP32 ONNX export comes from `results/checkpoint-3159`, not `email_classifier`. Source hashes, tokenizer, configuration and fresh inference parity identify it. **Release-model approval remains blocked by V10**; identifying the baseline does not authorize activation or establish a complete original training lineage.
- **V10 quality acceptance: FAIL, rating C.** No representative, untouched, human-reviewed final holdout is available. Existing development evidence is poor and does not justify bypassing the gate. No existing candidate has release approval.
- No training, export replacement, artifact promotion, database access/reprocessing, deployment or threshold change occurred. No final holdout was opened or consumed.

## 1. Mismatch source and model identity

The export's `source-sha256.json` records weights `97a26b679690d2ab8df85f4e5b8fab2b7c91c8011807ac04767c4a9790a1e3d4`. The existing `results/checkpoint-3159/model.safetensors` has exactly that SHA-256. The tracked [historical production report](../history/PRODUCTION_READINESS_REPORT.md) independently records the same path and hash. The 19 October private evaluation also records this exact weight/config/tokenizer identity.

The earlier closure compared the export with `email_classifier/model.safetensors`, whose SHA-256 is `1686c767582eab051298eb82fa048822b9c6142842f61b3a384f55e204f6902b`. These are distinct files with distinct tensor-payload hashes, not a formatting-only change. There is no evidence that checkpoint-3159 changed. Do not re-export the other model merely to make the filenames appear consistent.

Source config SHA-256 is `8ec1772000c970c33ad7ad840798d23bc4946012fe05f00a8f103992924e95ec`; exported config is `2d12a75c7d4f06922a3a71a6c712e8889c8d321d49f4209c2a7561946ed6173b`. Parsed configurations differ only by source `use_cache: false` being omitted after export normalization. The ten-label mapping, architecture, FP32 dtype, multilabel setting and 512-token position limit match. Tokenizer JSON is byte-identical: `435667fab0c06c165b1283ecb422497c37124f2d6a35b2ac73dc876332fc9518`. There is no observed label-index swap.

Existing export files remain unchanged: `model.onnx` SHA-256 `bdbba9a5946e4913c422cfcc7cc3eae762b75646a63c9ea53d2f47dcca363043`; `weights.bin` SHA-256 `a14f1c89a38aa4d42fa21437095d185b1178c988474c3d1f5c3450eb8cbdd9c7`. Experimental INT8 artifacts were not evaluated or substituted.

Bilingual product support requires separate English/Arabic acceptance. The legacy training-data audit reports English public data with no Arabic examples; neither the uncased tokenizer nor a passing export check establishes Arabic quality.

## 2. Existing training and evaluation evidence

| Artifact | Weight SHA-256 prefix | What can actually be established |
| --- | --- | --- |
| `results/checkpoint-3159` | `97a26b679690` | Preserved historical baseline and exact ONNX source; hash-bound development evaluation exists and is reproduced below. No `trainer_state.json`, original training report or frozen original split is present alongside it. Original training/generalization evidence cannot be reconstructed from the checkpoint number or optimizer file. |
| `email_classifier` | `1686c767582e` | Different weights; no adjacent training/evaluation report tying this file to release approval. Not the export source. |
| `results/checkpoint-1053` | `edaa03e3341e` | Epoch 1 / step 1053; 21 training-loss records, no evaluation log, best metric or selected checkpoint. Not sufficient for approval. |
| `results/checkpoint-2106` | `cd95ebd50523` | Epoch 2 / step 2106; 42 training-loss records, no evaluation log, best metric or selected checkpoint. Not sufficient for approval. |
| `results/checkpoint-3` | `d4d6bb468d5c` | Epoch 3 / step 3 metadata, zero log records, no best metric. No defensible quality conclusion. |
| `results/email-candidate-v2` | `abf4935dea0b` | Adjacent training report records 3 epochs, best epoch 3, 1,683/210/211 train/validation/test examples, seed 42, 256-token training and last two layers trained. The historical 100-row development evaluation matches these weights but scores only 29% top-one accuracy / 0.2900 top-one macro-F1. Not approved. |

The v2 report records public-test top-one accuracy 0.8957346 and **thresholded multilabel** macro-F1 0.7758638. The latter is not the release policy's top-one macro-F1. No adjacent frozen split manifest exists for this old run. Legacy public splits may overlap training; they cannot establish independent mailbox generalization. Training-report SHA-256: `589658b4e873f7885c2898082bccdeb91f83b33c9819dc61a844515256d969e3`.

The preserved sparse/multilingual experiments have documented recipes and evaluation reports. Their current artifact hashes match the 19 October comparison: grouped sparse `8cbe5ff7…`, character sparse `f9e4b0d5…`, multilingual original `a3ab4886…`, multilingual targeted `99e810c3…`. Historical development accuracy/top-one macro-F1: 39%/0.3104, 33%/0.2818, 39%/0.3036 and 43%/0.3410 respectively. The human-weighted sparse experiment's **out-of-fold**, not training-fit, result was 45%/0.2585. None is an accepted replacement. These consumed development results were not rerun to select a new model.

The final historical comparison explicitly records `selected_release_model: null`, `decision: BLOCKED`, `holdout_opened: false`. Its SHA-256 is `e18f6c4347cce61d5eeac94365c68ec69ad53ae10b4ab7ca70c86bdf86db7fc9`. The existence of training evidence is not a quality pass.

## 3. Datasets and holdout boundary

The inspected private classifier development export has 100 structurally valid human-review attestations, no ambiguous/weak/pending/invalid rows, and 100 unique cleaned texts. Its SHA-256 is `d764ab42121af03ca0432d081e90ef6c37811dd5ce27e3fc1c980bd55436db69`; it was unchanged by evaluation. Review tooling checks attestation structure, not who actually entered a label.

This is deliberately selected difficult **development** mail, already used in candidate comparisons. It is not representative, independent, or reusable as a final holdout. Business has zero examples; Finance has four and Travel two. Most other classes also fall below the required 20/class. Public English data and already-consumed authored bilingual challenge sets are diagnostic resources only.

Status mode confirms no `holdout.csv` in this classifier review directory. A filename-only check of local results/private-review evidence, excluding test fixtures and alternate Render worktrees, found no classifier `holdout.csv`, `review-policy.json` or `FINAL_EVALUATION_CONSUMED.json`. This is an observation about available local evidence, not proof that no external private holdout exists. No final labels were opened; no human labels or mailbox content are published here.

## 4. Fresh evaluation and language results

Fresh checkpoint-3159 inference reproduced the historical 19 October key metrics exactly: **32/100 correct, top-one macro-F1 0.2839, 14 Finance false positives and 18 wrong predictions at score >=0.80**. Finance false-positive rate is 14/96 = 14.58%; top-one ECE is 0.2888. These are difficult-development diagnostics, not general mailbox accuracy.

| Development slice | Correct / n | Top-one accuracy | Top-one macro-F1 |
| --- | --- | --- | --- |
| All reviewed development | 32/100 | 32.00% | 0.2839 |
| Arabic-heavy | 1/11 | 9.09% | 0.1000 |
| English | 20/56 | 35.71% | 0.3140 |
| mixed | 10/32 | 31.25% | 0.2658 |
| other | 1/1 | 100.00% | 0.1000 |

Direct fresh Torch-to-ONNX comparison passed on **111 inputs**: these 100 private development texts, ten existing public export probes and one overlength input. Top-one agreement: **111/111**; largest absolute difference across all ten sigmoid scores: **3.01003456e-06**, below the existing **0.0001** tolerance. The ten saved probe logits also matched (max absolute difference 4.70876694e-06). Export file hashes remain identical to the earlier evidence. This is an inference-equivalence check, not an accuracy pass or host-capacity benchmark.

Language labels are heuristics, not human language adjudications. The original evaluator counts texts with at least 20 characters in each script as mixed. That rule yields 56 English (20 correct), **one Arabic-only (0 correct)** and 43 mixed (12 correct). The existing development sampling rule removes URLs/addresses and calls a text Arabic-heavy at >=20 Arabic letters and >=65% Arabic share; this gives a more useful but still tiny Arabic-heavy slice. Both conventions are recorded, not selectively presented as an Arabic release benchmark. Macro-F1 here averages all ten labels, including unsupported labels; no metric was redefined to improve the result.

## 5. Unchanged acceptance gate and exact remaining action

`quality.classifier_release` status mode returned **passed=false, rating=C**, bound to the correct `97a26b67…` artifact. Exact blocker: **Representative human-reviewed final holdout evaluation is missing.** It did not evaluate development as if it were a holdout.

Policy remains `classifier-release-v1`: >=300 representative reviewed examples; >=20/class; >=50 English and >=50 Arabic; accuracy >=0.90; top-one macro-F1 >=0.85; every class precision >=0.80 and recall >=0.70; Finance precision >=0.95/FPR <=0.02; confident-error rate <=0.02; ECE <=0.10; language accuracy gap <=0.05; ambiguous fraction <=0.05. The existing difficult-development result also falls far below the headline accuracy/F1 targets, but is not a substitute final-test estimate.

The narrow remaining action is a **quality decision and the existing one-time acceptance process**, not another deployment fix:

1. Explicitly select/freeze the exact artifact for acceptance. Checkpoint-3159 is the proven preserved baseline; no evidence authorizes quietly substituting another existing candidate. Complete original training lineage remains unavailable and must stay disclosed.
2. Supply a separately sampled, untouched, human-reviewed representative mailbox holdout with the existing manifest, group-disjoint split and sampling-policy requirements. Do not relabel/copy these 100 development examples into it. Meet category/language coverage and freeze the artifact, manifest and policy hashes before opening final labels.
3. Generate complete predictions for that frozen artifact and run the existing `quality.classifier_release` final mode once. Record the immutable receipt and all original thresholds. If it fails, keep V10 failed.

Given the observed development errors, more labels or a re-export alone cannot be promised to fix quality. If the owner does not accept proceeding to final evaluation with this baseline, the next decision must explicitly authorize a **bounded classifier-quality improvement scope** or a release-contract change; neither is authorized or performed here. No automatic retraining, lowering thresholds, claiming English-only acceptance, or broad model search is justified.

## 6. Verification and privacy

- `python -m quality.classifier_release --review-dir <private-reviewed-development-directory> --artifact <checkpoint-3159/model.safetensors> --output <new-local-report.json>`: completed, gate failed as above; holdout not opened.
- `python -m pytest -q test_classifier_release.py quality/test_local_classifier_review.py test_onnx_classifier.py --basetemp results/v03-v10-20261024/pytest-gate --tb=short -rs`: **29 passed, 2 skipped, 2 subtests passed**, one Google Python-support warning, 7.71 seconds. Skips: opt-in synthetic review browser and opt-in saved-reference ONNX test. Fresh source/export evaluation above supplies independent artifact parity evidence; it is not represented as that skipped test passing.
- Initial default-temp attempt: 22 passed, 2 skipped, 2 subtests passed, 7 setup errors from Windows temp-directory permissions. Fresh workspace-local `--basetemp` resolved all seven; no application change was required.
- The read-only local runner calls the existing `human_development_eval.load_reviewed(expected=100)`, `model_scores('production', ...)`, `summarize`, and existing `review_sampling.describe`; it selects only the absolute checkpoint-3159 path, sets offline flags and bounded CPU threads, then compares with the unchanged ONNX artifact. It does not call the multi-model selection CLI or any trainer. Helper hashes, versions, input/artifact hashes and aggregate outputs are in [the sanitized machine-readable evidence](v03-v10-20261024.json). These two helpers reside in the preserved experimental workspace; they were inspected, not merged into the release branch. Private inputs are deliberately unavailable from a public clone.
- Local raw evidence/runner remain under ignored `results/v03-v10-20261024/`; mailbox inputs remain private. Only aggregate metrics, artifact hashes and documentation are committed. No model binaries, mail bodies, message IDs, addresses, reviewer identities or credentials are included.
- Application code is unchanged; unrelated frontend/backend/hosting audits and suites were not repeated.
