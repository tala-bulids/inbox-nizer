> Historical local development report, preserved from the accessible workspace. Its results are not new verification or a claim of production readiness. See ../../README.md for current setup and ../VALIDATION.md for this update.

# Ask Mail architecture review — 2026-10-13

**Acceptance target is NOT fully met.** A = ready; B = limited rollout after review; C = blocked on acceptance evidence. Ask: **C** (English destination resolution still fails on the real itinerary). Classification: **C** (no human gold labels yet). No production reprocessing is approved or performed.

| Area | Diagnosis / result |
|---|---|
| Scalar facts | Existing proven resolver retained; typed lookups with persisted but mismatched facts now abstain instead of falling into generated factual prose. |
| Travel | Existing same-record bundle preserved; flight-number labels added. Mixed/English verb morphology normalized without rewriting source values. Real Arabic query still returns six supported fields. |
| Recent status | Existing timestamp-constrained literal status retained. Explicit “were not selected” is quoted with its negation. Plural application questions may return separately cited status excerpts from several messages. |
| Existence | Vector similarity was the wrong decision procedure for sender existence. New bounded metadata lane verifies sender token identity and newsletter evidence, and works without embeddings. A body-only name mention cannot establish sender identity. |
| Digest | Broad updates previously followed ordinary RAG and abstained. Now SQL retrieves up to 120 recent owned emails, defaults to 14 days, extracts up to five complete meaningful sentences, suppresses obvious promotional sentences and exact duplicates, and cites each item. |
| Clarification | Real API two-step flow already worked for synthetic ambiguous trips; no demonstrated universal backend button defect. Added actual browser→API→PostgreSQL test, and preserved original question, selected ID and original history together. |
| Unsupported | Existing unsupported submarine query continues to abstain. No cited generated answer is promoted to verified truth. |
| Paraphrases | Generic same-language and mixed-language fixture variants pass. Real English “Jeddah” still does not match an Arabic-only destination; source contains airport codes, but no verified general alias resolver is available. It now abstains rather than generating from the wrong email. Mixed unspecific “my flight” clarifies multiple trips. |

## New request flow

Bounded prior questions → deterministic QueryPlan → strategy-specific owned candidates → existing fact/rule ranking or metadata/temporal selection → supported fields/excerpts → citation validation → existing API verification states.

- Dense + persisted fact lanes remain; a bounded lexical lane over sender/subject/chunk qualifiers is fused and deduplicated before existing ranking. Explicit min_score still applies. OwnedSession scopes queries before LIMIT.
- Existence/digest avoid E5 and Qwen. They build an internal AnswerPlan of metadata or exact body spans. Metadata-only sources use chunk_id=0 when there is no stored chunk; frontend links the email ID.
- No classifier output or extracted task is used as digest truth. Digest is an attributed excerpt list, not unrestricted semantic summarization. Importance detection remains conservative and lexical; thread consolidation is not comprehensive.
- Status timeline: existing explicit organization+application-reference matching can identify the latest status. Plural status answers keep messages separate. A complete historical timeline is not implemented.
- Multi-turn: optional POST history has at most four prior questions, each at most 2,000 characters. The authenticated React session keeps it only in memory, clears on reload/logout, and never sends previous answer prose as evidence. Short explicit “only / بس / فقط” follow-ups inherit the prior topic and retrieve again. This is bounded narrowing, not unrestricted conversation understanding.
- Citation checks, source_supported vs generated_synthesis, tenant isolation, CSRF, auth and Gmail are unchanged. No new external inference or model is introduced.

## Measured real mailbox comparison (read-only)

| Case | Before | After | After seconds | LLM calls |
|---|---|---|---:|---:|
| travel_ar | answered | answered (deterministic_fact) | 9.530 | 0 |
| travel_en | insufficient_evidence | insufficient_evidence (—) | 1.041 | 0 |
| travel_mixed | insufficient_evidence | needs_clarification (—) | 0.284 | 0 |
| digest_ar | insufficient_evidence | answered (extractive) | 0.242 | 0 |
| digest_en | insufficient_evidence | answered (extractive) | 0.055 | 0 |
| existence | insufficient_evidence | answered (extractive) | 0.050 | 0 |
| status | insufficient_evidence | insufficient_evidence (—) | 0.052 | 0 |
| unsupported | insufficient_evidence | insufficient_evidence (—) | 18.198 | 1 |

Arabic travel actual output:

موعد رحلتك: 16-Oct-2026 (2026-10-16)؛ وقت المغادرة: 11:35؛ وقت الوصول: 13:25؛ المغادرة من: الرياض؛ الوجهة: جده؛ رقم الحجز: KI76YH. [email_id=4]

Existence recovered emails 4018, 94, 176, 9 and 60. Both digest languages cite the same five emails: 4015, 4009, 4004, 4002, 3997. Bodies are not reproduced in this report. The chosen five digest items still need human relevance/importance review.

Known-source retrieval at returned K=8: Arabic travel 1/1; English destination 0/1. This tiny diagnostic is NOT corpus-wide Recall@K. No defensible aggregate MRR/NDCG, factual accuracy, false-positive or false-abstention rate is claimed without adjudicated targets. The English case remains a known false abstention. Recent camp status has no independently labelled current target, so abstention cannot be scored as correct rejection.

Latency above is one local run, not a percentile benchmark. First Arabic request includes encoder cold load. Digest/metadata paths were 0.05–0.24 seconds; unsupported model fallback took 18.2 seconds. Detailed dense/fact timing remains in existing internal retrieval telemetry. No reranker latency is reported because it did not run.

## Reranker decision

BAAI/bge-reranker-v2-m3 was reviewed against its official model card: https://huggingface.co/BAAI/bge-reranker-v2-m3 . Prepared an isolated 32-candidate, batch-one, CPU benchmark command with resource guard. Observed free RAM initially 1.53 GiB, then 0.60 GiB during evaluation; guard requires 5 GiB headroom. **Not downloaded, not loaded, not benchmarked, not deployed.** No quality improvement is claimed. Local judged candidate pairs and adequate free RAM are prerequisites for its comparison.

## Classification gold workflow

Exported 332 private real-mail examples to the local classification-review-20261013 directory outside the repository: 184 development, 148 holdout. Stratification covers predicted category, language, confidence and split; sender-domain/normalized-subject template groups stay in one split. Predicted labels are hidden in the reviewer CSV. Gold labels/reviewer/ambiguity fields are blank. Human gold count: **0**.

Fill gold_label using the supplied taxonomy and mark ambiguous cases rather than forcing them. REVIEW.md documents Business vs Job Application vs Finance policy. Do not train or select on holdout labels; use the holdout once after candidate selection. Template grouping is preliminary and still needs duplicate/leakage review before declaring the holdout sealed.

No classifier retrained or deployed this turn. Previous authored 40-case results remain production 32.5% accuracy / 0.3624 macro F1 versus candidate 92.5% / 0.9260; they are consumed diagnostics, not representative mailbox validation. The public diagnostic regression and calibration limitations still block deployment.

## Tests and files

- Backend: **1151 passed, 1 opt-in browser test skipped**, one existing Starlette deprecation warning.
- Opt-in real browser test separately: **1 passed** against isolated PostgreSQL. All database fixtures rolled back; conftest blocks production connections.
- Frontend: **119 passed**; API generation, typecheck, lint, format check and production build passed. Responsive ui:check passed at 1440/820/390, including warnings, no private browser storage and mobile focus restoration. Build has existing dependency annotation warnings.
- Scoped git diff --check passed. Whole-tree pre-existing trailing whitespace at test_main.py:37 is not part of this change.

Production files: new ask_plan.py, ask_mailbox.py; changed rag_api.py, rag_service.py, rag_candidates.py, question_understanding.py, rag_bundle.py, rag_status.py.
Frontend: src/features/ask/AskPage.tsx, AskSession.tsx; src/test/ask-search.test.tsx; openapi.json; src/api/generated/schema.d.ts; new scripts/check-ask-integration.mjs.
Tests/tooling: new test_ask_planner.py, test_ask_browser.py; quality/mailbox_gold.py, quality/final_ask_eval.py, quality/reranker_benchmark.py; this ASK_FINAL_REVIEW.md. Ignored benchmark artifacts are in results/ask-final-20261013/. Historical unrelated dirty files were preserved.

**Production data modified: NO.** No backfill, resync, reclassification, stage, commit or push.

## Remaining acceptance blockers

1. Reliable cross-language destination/entity alignment and broader independently labelled Ask benchmark.
2. Reranker comparison requires RAM headroom and judged candidate pairs; current results cannot determine whether it is worth deploying.
3. Human classification labels and duplicate adjudication before representative candidate/calibration evaluation.
4. Richer digest importance/thread grouping, complete application timelines and general multi-turn/multi-email reasoning remain narrower than the requested final assistant.
