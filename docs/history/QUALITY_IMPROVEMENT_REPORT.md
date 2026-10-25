> Historical local development report, preserved from the accessible workspace. Its results are not new verification or a claim of production readiness. See ../../README.md for current setup and ../VALIDATION.md for this update.

# inbox-nizer — quality evaluation, 12 October 2026

## Decision

**Classification: B. Tasks: B. Ask: B.** Improvements are measurable; none has enough independent real-mailbox ground truth to justify an A. The multilingual classifier is an **offline candidate, not the production model**. Production predictions/tasks and all original messages remain unchanged. No production reprocessing, backfill, schema change, staging, commit, push, or external inference occurred. Frontend and API response schemas were not changed.

## Findings and scope

- The deployed classifier is `results/checkpoint-3159`. `email-candidate-v2` exists but is not selected by the default runtime. Correct ten-label mappings were verified; there is no demonstrated label-index swap. Artifact hashes are recorded.
- Training data has 2,105 rows, no Arabic examples, 1,002 placeholder-containing rows, one contradictory exact duplicate group (two rows), 130 near-duplicate pairs, including 38 with differing label sets. Placeholder presence suggests template-heavy data; it is not proof every example is synthetic or wrong.
- Business has 939 usable label occurrences versus 120 Promotions and 122 Job Application. Multi-label examples are common. The old cleanup unions contradictory exact labels and the old random split does not group near-duplicate templates. Sender/domain/thread metadata is absent, so those leakage dimensions cannot be ruled out.
- The previous best-checkpoint metric was thresholded multi-label F1 while production always returns one argmax category, even at low confidence. New evaluation reports the actual top-one decision, per-class precision/recall/F1, confusion and confidence bins separately.
- Public examples are very short: maximum 123 tokens, none beyond 256. In a deterministic read-only sample of 492 real emails, 185 contain Arabic and 344 exceed 512 tokens (456 exceed 256; median 1,187). Truncation exposure and language mismatch are established; the exact causal share of individual errors is not.
- Stored predictions do not record which model artifact produced them, and enrichment stages skip unchanged inputs. A code/model change cannot correct already-stored predictions by itself.
- A read-only aggregate query found 3,927 emails, 3,927 predictions, 458 tasks and 1,590 facts. Finance review flag ID 3958 combines professional/networking wording with stored Finance at confidence 0.284. This is a review flag, not human-labelled ground truth. No private bodies were copied to fixtures or reports.

## Classifier experiment

Exact contradictory groups were quarantined rather than unioned. Connected components of character-ngram cosine similarity >= 0.9 are kept within a split; identifiers are normalized before clustering. Seed 42 gives 1,672 train / 214 validation / 217 test rows. Twenty generic bilingual development examples were added to training; a separate 20-example bilingual final set was authored before tuning and evaluated after selection. No mailbox text is training data.

The local multilingual E5-small encoder is frozen. Only a balanced one-vs-rest logistic head is trained: liblinear, max_iter=1000, C in {0.1,1,10,100}, seed 42, 512 tokens, batch 4, normalized query-prefixed embeddings. Validation top-one macro-F1 chooses C=10 (0.7134; validation accuracy 0.9159). No transformer epochs, learning-rate schedule or early stopping applies to this frozen-encoder/convex-head experiment. The prior English model architecture was not silently replaced.

| Model | Public accuracy / macro-F1 | Bilingual accuracy / macro-F1 | Bilingual Finance FP |
|---|---:|---:|---:|
| checkpoint-3159 | 0.912 / 0.647 | 0.400 / 0.449 | 1 |
| email-candidate-v2 | 0.848 / 0.628 | 0.350 / 0.321 | 2 |
| multilingual-probe | 0.880 / 0.649 | 0.850 / 0.813 | 0 |

**Limitations:** the public holdout may have been seen by legacy checkpoints; their old split is not reconstructable. These are diagnostic comparisons, not unbiased legacy generalization estimates. The bilingual test is tiny and author-labelled, not an inbox-wide accuracy estimate. It is now consumed and must not select future candidates.

### Bilingual per-class precision / recall / F1

| Category | Current | Candidate |
|---|---:|---:|
| Business | 0.09 / 0.50 / 0.15 | 0.00 / 0.00 / 0.00 |
| Customer Support | 1.00 / 0.50 / 0.67 | 1.00 / 1.00 / 1.00 |
| Events & Invitations | 1.00 / 0.50 / 0.67 | 1.00 / 0.50 / 0.67 |
| Finance & Bills | 0.50 / 0.50 / 0.50 | 1.00 / 1.00 / 1.00 |
| Job Application | 1.00 / 0.50 / 0.67 | 0.67 / 1.00 / 0.80 |
| Newsletters | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 |
| Personal | 0.50 / 0.50 / 0.50 | 0.50 / 1.00 / 0.67 |
| Promotions | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 |
| Reminders | 1.00 / 0.50 / 0.67 | 1.00 / 1.00 / 1.00 |
| Travel & Bookings | 1.00 / 0.50 / 0.67 | 1.00 / 1.00 / 1.00 |

Full public and bilingual confusion matrices, class metrics, confidence distributions and validation trials are in `results/quality-20261012/classification.json`. On single-label bilingual gold the matrices are ordinary confusion matrices; on multi-label public gold each row contributes 1/number-of-gold-labels to avoid inventing a primary gold label.

The candidate fixes the promotional-installment/Finance confusion in this small test, and improves Arabic support, application status, newsletters and travel. It still mislabels both professional-networking examples (Job Application/Personal) and the Arabic invitation (Personal). Sender-signature stress changes 4/20 candidate predictions versus 3/20 current predictions. This is an important remaining robustness failure, not an acceptable A.

Confidence is not a guarantee: bilingual top-one ECE is 0.273 current versus 0.230 candidate, from only twenty cases. No uncertainty category or API change was introduced; no calibration guarantee is claimed. A independently labelled, representative calibration set is needed before a minimum-confidence product policy.

## Tasks and deadlines

Root causes: conjunction splitting discarded the actor/condition; polite-prefix removal treated condition fragments independently; Arabic action nouns were accepted as status statements; mandatory-registration context leaked across the whole message; an action-like subject could revive an already-completed action; date matching accepted event “on Friday” as a deadline.

Changes preserve conditional sentences intact, conservatively reject inherited non-user/negated/footer scope, reject informational registration headings, limit registration context to the adjacent sentence, and bind subject completion to the same action/object. Different conditions are not deduplicated together. Deadline selection ignores event “on” dates, attendance timing and dates inside the conditional premise, but still keeps explicit action due constraints. Public functions, output keys, five-task cap and local-only operation are unchanged.

| 44-case labelled diagnostic suite | Before | After |
|---|---:|---:|
| Message-level detection precision | 64.5% | 100.0% |
| Recall | 95.2% | 100.0% |
| F1 | 76.9% | 100.0% |
| Negative-message false-positive rate | 47.8% | 0.0% |
| Deadline phrase precision | 60.0% | 100.0% |
| Deadline recall | 90.0% | 100.0% |

Positive cases: 21; negative cases: 23. Correct retained action/actor/condition: 16 -> 21. Predicted task items: 32 -> 21. Deadline matches: 9/15 -> 10/10. Calendar normalization is also exercised by the existing deadline tests. These cases guided development: perfect regression scores are NOT a production precision claim.

Read-only drift sample (492 owned emails): 74 -> 61 proposed tasks; 1 -> 0 deadline phrases. Those numbers alone do not establish quality; changed IDs are retained for review. Treating bare “on” dates as non-deadlines may miss some intended due dates. Short noun fragments, remote context and subtle actor/completion language remain limitations of a conservative rule-based extractor. No stored tasks were replaced.

## Ask: stage diagnosis and runtime evidence

The role parser recognized a narrow noun vocabulary and missed colloquial travel/arrival verbs, the “كم” question form and “موعد” date wording. Deadline candidate retrieval and field resolution also used inconsistent bilingual roles. Question-only morphology now maps a small set of verb paradigms to existing roles, preserving every remaining place qualifier. Deadline labels and field qualifiers share a canonical role. No generation prompt, embedding model, vector K, citation validator, security policy or source text is weakened or rewritten.

With identical correct evidence, supported role lookups improve 7/11 -> 11/11; unsupported cases remain 4/4 rejected. PostgreSQL tests exercise Search plus the actual candidate/evidence/persisted-fact/service path, including ambiguity and citations. Their encoder is deterministic/fake: real embedding behavior is measured separately below.

Twelve real queries were run before/after through the current local Qwen3-0.6B provider where needed, using owned sessions inside PostgreSQL READ ONLY transactions and persisted facts (preview=False). Bodies and model prose are omitted; reports retain IDs, selected scalar facts, modes, timing and answer hashes.

| Runtime question | Before | After |
|---|---|---|
| متى بسافر؟ | needs_clarification | needs_clarification |
| متى رحلتي؟ | needs_clarification | needs_clarification |
| متى السفر؟ | needs_clarification | needs_clarification |
| متى بروح جدة؟ | insufficient_evidence | needs_clarification |
| وش موعد رحلتي؟ | insufficient_evidence | needs_clarification |
| كم وقت الوصول؟ | insufficient_evidence | needs_clarification |
| متى أوصل؟ | insufficient_evidence | needs_clarification |
| وش آخر موعد؟ | needs_clarification | needs_clarification |
| متى آخر يوم؟ | needs_clarification | needs_clarification |
| متى ب اسافر لجده؟ | answered | answered |
| What is the departure time to Jeddah? | insufficient_evidence | insufficient_evidence |
| What is the submarine booking number? | insufficient_evidence | insufficient_evidence |

The four repaired false abstentions now request clarification rather than guessing among multiple matching records. Do not count them as four new factual answers. The explicit Arabic travel lookup still returns **16-Oct-2026**, citation email 4, without LLM. The English departure query still fails at retrieval/qualifier coverage: email 4 is absent from both Search top ten and Ask returned chunks. The unsupported submarine query still abstains. Aggregate runtime: current 1 answer + 5 clarification + 6 abstentions; improved 1 answer + 9 clarification + 2 abstentions. Thus Ask is B, not A.

## Performance and tests

Warm CPU single-email check, identical twenty short bilingual inputs, two threads, three warmups: current mean 25.7 ms (p95 37.3), candidate 16.2 ms (p95 18.8). This does not predict long-mail throughput. The first public baseline timing was affected by cold/resource stalls and is not used as a speed comparison. Task diagnostic mean is approximately 0.087 -> 0.094 ms/case. Warm real deterministic/clarification Ask is roughly 0.3–0.46 seconds; first-call model loading is about 8–9 seconds. Actual fallback generations take roughly 13–14.5 seconds; the previously unnecessary arrival generation is now skipped.

Full backend: **1105 passed** (17.15 seconds); **96 new focused tests passed**, one existing Starlette/httpx deprecation warning. Existing isolation, prompt-injection, grounding, citation, provider-failure and API tests pass. One old grounding test was made sequence-independent: a wrong numeric value occurring inside an email citation ID is no longer confused with the factual answer. The attendance deadline test now uses a real submission action; attendance dates explicitly test as non-deadlines.

Changed-file diff check passes. Whole-tree `git diff --check` still reports pre-existing trailing whitespace at `test_main.py:37`; that unrelated historical edit was preserved. Frontend tests were not run because no frontend/shared response schema changed.

## Artifacts, deployment and reprocessing

New offline artifact: `results/quality-20261012/multilingual-probe.joblib`, with `candidate-metadata.json`, split/challenge manifests, hashes, reports and logs. Existing model files were not overwritten. No trained GGUF/embedding retrieval model changed. The server was not restarted to deploy these changes.

**Do not bulk reprocess yet.** Review the changed task IDs and independently label a representative bilingual mailbox sample before adopting the candidate or replacing stored tasks. Any approved later reprocessing needs a DB backup, new model/extractor stage versions, dry-run diff, resumable batches, idempotency and an audit trail. The current patches do not retroactively fix stored results.

## Exact files changed this phase

- Production: `task_extractor.py`, `task_context.py` (new), `deadline_extractor.py`, `fact_roles.py`, `question_understanding.py` (new), `rag_candidates.py`.
- Tests: `test_quality_regressions.py` (new), `test_quality_data.py` (new), `test_deadline_extractor.py`, `test_rag_grounding.py`.
- Evaluation/training: `quality/__init__.py`, `quality/dataset.py`, `quality/metrics.py`, `quality/cases.py`, `quality/classification_cases.py`, `quality/classification.py`, `quality/classifier_stress.py`, `quality/evaluate_rules.py`, `quality/mailbox_rag.py`, `quality/mailbox_tasks.py`, `quality/latency.py` (all new).
- Report: `QUALITY_IMPROVEMENT_REPORT.md` (new). Ignored generated artifacts/logs: `results/quality-20261012/`. Read-only baseline copies: the current Codex workspace `quality-baseline/`.

## Reproduce

Run from the project directory using its environment; cached models/data are required. No hosted inference is used.

```powershell
$env:PYTHONUTF8='1'
$env:HF_HUB_OFFLINE='1'
$env:OMP_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
.\env\Scripts\python.exe -m quality.classification
.\env\Scripts\python.exe -m quality.classifier_stress
.\env\Scripts\python.exe -m quality.evaluate_rules --output results/quality-20261012/rules-after.json
.\env\Scripts\python.exe -m quality.latency
.\env\Scripts\python.exe -m pytest -q
```

Read-only mailbox commands require an explicit existing `--user-id` and `--output` path: `python -m quality.mailbox_rag` / `python -m quality.mailbox_tasks`. Set `RAG_MODEL_PATH` to the existing local GGUF for real generation. The optional `--baseline` argument uses the saved pre-change modules. Do not publish private evaluation outputs.

Background references: [English DistilBERT model card](https://huggingface.co/distilbert/distilbert-base-uncased), [E5 multilingual model card and classification prefix guidance](https://huggingface.co/intfloat/multilingual-e5-small), [scikit-learn calibration guidance](https://scikit-learn.org/stable/modules/calibration.html).
