> Historical local development report, preserved from the accessible workspace. Its results are not new verification or a claim of production readiness. See ../../README.md for current setup and ../VALIDATION.md for this update.

# inbox-nizer final readiness pass

Evidence collected 15–17 October 2026. **Public release is blocked.** The repository now has stronger safeguards, conservative extraction, broader Ask behavior and a passing application test suite. These results do not establish representative mailbox accuracy or an operational public deployment.

Evidence artifacts are local under `results/release-readiness-20261015/` and deliberately ignored by Git. They are development records, not public benchmark material. No paid inference, hosted inference, external publication, staging, commit or push was performed.

## 1. Main root causes

- Classification data is a poor proxy for this bilingual mailbox: 2,105 public rows, no Arabic rows, 1,002 placeholder-containing rows, overlapping labels, one exact contradictory group and 38 near-duplicate pairs with different labels. Sender metadata is absent, so sender-domain leakage cannot be measured for that source. Two contradictory rows are now quarantined; 130 near-duplicate pairs are grouped. The audited public split contains 1,683 training, 216 validation and 204 test rows.
- The running English DistilBERT artifact and raw sigmoid confidence do not establish bilingual correctness. A label-contract check protects against mapping corruption, but it cannot cure poor annotations, ambiguous categories, truncation or model capacity. No single sender-specific cause was proved for the reported professional-mail/Finance failure, and no sender/domain/subject exception was added.
- Task rules accepted marketing and optional participation language. Deadline extraction attached document/event dates to nearby actions. The expanded diagnostic set exposed these failures even though the older 44 examples already passed.
- Ask needed separate metadata and time-window paths, geographic equivalence, cohesive facts, and presentation that retained supported meaning. Previously, cached embedding startup still attempted network access. Alias expansion also multiplied costly SQL comparisons.
- Public operations remain incomplete: synchronous Gmail sync can paginate and enrich an entire mailbox/delta while holding a transaction and account lock; deployed TLS/Google flows, capacity and restore procedures have not been demonstrated.

## 2. Classification: model, selection and metrics

**Production model unchanged:** `results/checkpoint-3159/model.safetensors`, SHA-256 `97a26b679690d2ab8df85f4e5b8fab2b7c91c8011807ac04767c4a9790a1e3d4`. No new candidate passed release gates or replaced it.

For context only, the historical `DEEPER_QUALITY_REPORT.md` records the current model at 32.5% accuracy / 0.3624 macro F1, five Finance false positives and five high-confidence errors on 40 authored bilingual challenges. Those results were not rerun as a fresh test here. The historical multilingual candidate's stronger 40-case result coexisted with a public diagnostic regression, so it also lacks release evidence. No representative production-model accuracy is available.

Training now uses deterministic seeds, connected template/available-domain groups, contradiction quarantine, class-distribution reports, validation-based checkpoint selection, early stopping and explicit opt-in test evaluation. Inference validates category order and token limits and loads models lazily. Metrics include per-class precision/recall/F1, weighted multi-label confusion, Finance false positives, the three requested confusion pairs, high-confidence errors and calibration diagnostics. Raw confidence remains uncalibrated.

A seven-candidate offline character TF-IDF/logistic-regression sweep used public validation plus **previously consumed authored bilingual development examples**. The old examples named FINAL/HOLDOUT in historical modules are explicitly treated as development here. No private holdout or public test predictions were evaluated. These are experiments, not interchangeable production model artifacts.

| C | Public validation accuracy, n=216 | Public macro F1 | Authored bilingual macro F1, n=60 |
| --- | ---: | ---: | ---: |
| 0.3 | 0.8380 | 0.6788 | 0.4488 |
| 1 | 0.8426 | 0.6799 | 0.6803 |
| 3 | 0.8611 | 0.6921 | 0.7381 |
| 10 | 0.8611 | 0.6918 | 0.7516 |
| 30 | 0.8426 | 0.6818 | 0.7669 |
| 100 | 0.8287 | 0.6638 | 0.8116 |
| 300 | 0.8287 | 0.6578 | 0.7933 |

The predeclared average-development score selected C=100, then worsened at C=300; the bounded seven-candidate run ended. This exposes a tradeoff rather than a release improvement: public macro F1 declines beyond C=3. C=100 has 26 high-confidence public errors, 2 public Finance false positives and public ECE 0.1329; its authored bilingual ECE is 0.2768. **Reject all these candidates for production.** Full class/confusion/configuration/hash records and the experimental checkpoint are in `classifier-sweep-final/`. The earlier three-candidate run is preserved separately.

A second grouped word/character baseline workflow (`quality.classifier_selection`) jointly groups public and authored training supplements, compares six balanced/unweighted heads, records a hard-negative review queue and selects only on its grouped validation split. It selected balanced C=3: validation n=217, accuracy 0.8894, macro F1 0.7287, zero Finance false positives, **21 high-confidence errors**, ECE 0.0672. Arabic validation has only four examples (three correct), versus 213 English examples; this cannot establish parity. The 24-error review queue retains public/authored label provenance and does not create human labels. The run took 69.45 seconds with about 201 MiB final process RSS. Its checkpoint, six configurations, full metrics, split manifest and hashes are in `grouped-classifier-selection/`. It too is rejected for production. Different splits make its numbers unsuitable for a direct ranking against the table above.

The real private review directory was not available at the supplied location/context. A request for its location and review status remains unanswered; **the human-reviewed count is unknown, not zero**. No human labels were invented and no final private holdout was opened. The existing stratified export workflow explicitly declares itself diagnostic and nonrepresentative.

`quality.classifier_release` requires frozen artifact/label/policy/manifest hashes and human-review attestations, refuses selection-used or nonrepresentative evidence, and consumes the final holdout once. Its current status is **C / failed** in `classifier-gate.json`. Attestation validation cannot prove who actually performed a review.

Release thresholds are fixed in that policy: at least 300 representative examples, 20 per class and 50 per Arabic/English; accuracy ≥0.90, macro F1 ≥0.85, class precision ≥0.80/recall ≥0.70, Finance precision ≥0.95/FPR ≤0.02, confident-error rate ≤0.02, ECE ≤0.10 and language accuracy gap ≤0.05. These are acceptance targets, not achieved metrics.

## 3. Task and deadline extraction

Rules now reject generic purchase/cart/collection language and optional public/free participation unless context establishes obligation. Dates describing issuance, receipt, sending or an event are excluded as action deadlines. Conflicting deadline constraints preserve the task while withholding a date.

The same expanded **72 authored development cases** were measured before and after; this set was used to develop the fixes, so its result is not held-out mailbox accuracy.

| Measure | Before TP / FP / FN | After TP / FP / FN |
| --- | --- | --- |
| Email-level task detection | 34 / 6 / 0 | 34 / 0 / 0 |
| Individual action extraction | 36 / 6 / 0 | 36 / 0 / 0 |
| Correct task/deadline associations | 19 / 8 / 0 | 19 / 0 / 0 |

Detection precision improved from 0.85 to 1.00 on these cases; action precision from 0.8571 to 1.00; deadline-association precision from 0.7037 to 1.00. Recall is 1.00 in each diagnostic denominator. Date-string recognition alone is not counted as a correct association. See `tasks-expanded-before.json`, `tasks-expanded-after.json`, `quality/task_acceptance.py` and `test_task_acceptance.py`. Existing stored tasks were not regenerated.

## 4. Ask architecture

The bounded planner chooses selected-email, fact/travel, status, sender/existence, recent digest or fallback retrieval. OwnedSession applies tenant scope before ranking and limits. Dense E5 retrieval, persisted roles and bounded lexical aliases are fused, reranked by existing application checks and audited for evidence. Relational verification preserves same-record and qualifier constraints; ambiguous records require clarification.

Deterministic fact bundles and attributed excerpts answer supported questions without Qwen. Temporal and metadata questions bypass ordinary single-document RAG. Qwen3-0.6B remains a local fallback; citation validation and the generated/unverified distinction remain in place. Unsupported output is withheld; an available supported application answer can be used instead. This is still a bounded assistant, not unrestricted multi-email reasoning.

## 5. Ask read-only benchmark

Twelve fixed development probes were run against the owned real mailbox using a PostgreSQL read-only repeatable-read transaction. Artifacts record states, source IDs, answer hashes, memory and latency, not private message bodies. Per-case savepoints isolate query failures. **These probes have no human-judged expected-answer/source set. Correctness, wrong-source and false-abstention rates are therefore unknown.**

The final run (`mailbox-optimized.json`) returned eight supported responses and four abstentions, with no execution errors. The successful states comprise four travel paraphrases, three digests and one sender/newsletter query. The university sender query and two application-status queries abstained; these may be correct absences or false abstentions and require review. The unsupported booking query abstained after local generation.

Earlier artifacts are retained: the first ownerless-user probe was not representative; initial owned runs encountered offline model-loading/SQL errors; one run's aborted transaction contaminated later cases. These are failures, not omitted successful trials. The final runner fixes error isolation. Before/after runs across days are not a controlled randomized latency benchmark.

## 6. Arabic/English parity

Arabic, English and mixed travel queries resolved the same record; Arabic/English recent digests chose the same source set in the fixed probes. Synthetic tests cover bilingual planning, status polarity, extraction, UI direction and source navigation. This establishes specific regressions, **not overall parity**. Classifier representative bilingual metrics and human-rated Ask/task parity remain unavailable. Source excerpts retain their original language; UI labels follow the selected interface language.

## 7. Cross-language entities

Offline `geonamescache==3.0.0` supplies generic GeoNames aliases rather than a destination dictionary. Jeddah/جدة and several other cities are tested in both directions. Aliases nominate evidence; they do not supply travel facts or turn city names into airports. Ambiguous names, unknown translations and airport-code inference are deliberately unresolved. The database covers cities of at least 15,000 population, not every place or institution. Some Arabic aliases, including an ambiguous Riyadh spelling, can conservatively abstain. Attribution and limits are in `GEOGRAPHIC_DATA.md`.

## 8. Recent digest

The temporal path reads at most 120 owned messages plus an overflow sentinel, ranks complete supported sentences by security/application/payment/travel/professional signals, suppresses clear marketing, and returns at most five cited items. It deduplicates exact content and explicit RFC thread references, retaining the newest message in a thread. Shared subject text alone never merges unrelated records. Time scope and candidate truncation are disclosed. Priority is independent of the untrusted classifier label.

This is concise attributed extraction, not a judged high-quality abstractive summary. Lexical importance signals can miss subtle developments, lack of references limits thread grouping, and a crowded window can hide older important items behind the candidate cap.

## 9. Existence and status

Sender queries use owned sender metadata and topic/type checks. Unqualified existence does not invent a recent window. Answers provide a count/latest date with “at least” when displayed matches are capped. Matching does not equate an Arabic institution description with every English organization automatically.

Application handling distinguishes explicit acceptance, explicit rejection, missing evidence and multiple candidates. Absence says no matching message was found in scope; it never asserts rejection. Vague recent requests use and disclose a 14-day window; explicit periods are honored. Calendar boundaries currently use disclosed UTC, not a stored per-user timezone. Broad finance aggregation and arbitrary plural-application summaries still have limited coverage.

## 10. Multi-turn behavior

Up to four recent questions/context turns remain in the mounted Ask session; no mailbox conversation is persisted in localStorage. Reload/logout clears it. Follow-ups retain a bounded topic/qualifier context and reverify owned sources. Prior assistant text cannot become mailbox evidence. This supports the tested follow-up patterns, not unlimited conversational memory.

## 11. Clarification

Multiple matching records produce bounded source-backed choices rather than an invented selection. Selection validates ownership/context and rechecks evidence. Synthetic tests and the opt-in browser-to-isolated-PostgreSQL test cover an actual clarification round trip. The latter uses the application backend with synthetic mail; it is not a live Google/production-mailbox browser test.

## 12. Frontend UX

The retro design is preserved. Category labels are centralized and translated; Search and Ask copy is simplified. Main answers strip technical citation markers and render human dates; separate collapsible sources retain provenance and safe email links. Supported excerpts preserve conditions and negation. Generated synthesis retains a visible warning. Inbox keeps category multi-select and priority; Tasks keeps its own ordering/deadline controls. Returning from Email Detail restores originating page/filter state.

Production-browser smoke passed at 1440/820/390 widths in Arabic and English, without horizontal overflow or page errors; mobile menu focus restoration passed. Screenshots were inspected, including mobile Ask and desktop login. Long/repeated synthetic text is an intentional layout stress fixture, not an example of production answer quality. Browser APIs were mocked except for the separate isolated-backend clarification check.

## 13. Google-login UX

Production displays the requested welcome text and one primary Google action. Development token entry is development-only, and the server rejects its exchange route in production. Application login remains separate from Gmail consent. Users without a connected account go to Settings; connected users reach Inbox. Real production consent/login remains unverified and admission remains invitation/existing-account based.

## 14. Security findings and fixes

This pass enforced the server-side development-only browser exchange, removed the unused profile scope, bounded Google token/certificate requests, suppressed private validation payloads and exception details, and removed identifiers from affected pipeline/sync logs. SQL parameters are hidden; pool/connect/statement/lock waits are bounded. Readiness checks schema and runtime-role privileges without mailbox access.

Existing state/nonce/PKCE, verified Google identity, encrypted Gmail credentials, Secure/HttpOnly session design, session-bound CSRF, owned-query scoping and source validation remain enforced by tests. The audited runtime DB role lacked superuser/create-role/create-database/bypass-RLS and ownership privileges. This is tested application hardening, not an independent penetration test or an assertion about a public host's cookie/TLS behavior.

## 15. Deployment

`deploy/` now contains a same-origin nginx example, single-worker systemd example, health checks, sanitized monitoring guidance and a backup/restore/migration/rollback runbook. These files have not been installed or executed on a Linux target; hostnames, keys, permissions, capacity and recovery still require validation. Python dependencies are not a fully locked reproducible production environment.

Google public approval, verified domain, public homepage/privacy/support/deletion process and actual production callback evidence are missing. Gmail read-only is a restricted scope; server handling of that data falls under Google's verification/security-assessment requirements. See the official [scope documentation](https://developers.google.com/workspace/gmail/api/auth/scopes) and [restricted-scope verification guidance](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification), checked during this pass. No assessment, paid service or console change was initiated. `deploy/GOOGLE_PUBLIC_RELEASE.md` records the operator checklist.

Unbounded initial/history sync is a concrete engineering launch blocker. It needs persisted continuation, bounded message/time batches, short transactions and mixed interactive/sync load testing. An example proxy timeout or concurrency limit does not solve that design gap. Disconnect preserves imported mail and is not full data deletion; the existing operator deletion workflow must be made operationally accessible and tested.

## 16. Performance and resources

| Final real-mailbox probe | Observed seconds |
| --- | ---: |
| First travel request, cold process/models | 35.34 |
| English travel | 3.02 |
| English travel paraphrase | 1.95 |
| Mixed-language travel | 4.09 |
| Three digest requests | 0.16–0.50 |
| Newsletter existence | 0.067 |
| University/status abstentions | 0.033–0.135 |
| Unsupported fallback with local LLM | 42.35 |

The three warm travel requests previously took 10.15/7.69/12.67 seconds. Replacing repeated per-alias SQL normalization with bounded escaped literal regex alternatives preserved their answer hashes and source records while reducing observed latency. Cold GeoNames/model loading and long fallback generation remain concerns. The profiler and both snapshots are preserved; this is sequential local evidence, not p95 capacity.

The synthetic sequential API benchmark measured p50/p95 milliseconds: mocked Google-login server work 38.39/46.79; session restore 7.09/9.06; Inbox first page 51.19/59.60; offset-800 page 53.70/62.19; Tasks 45.94/56.58; mocked no-change sync 19.36/25.76. It excludes external Google, TLS/proxy, model work and concurrent load. See `runtime-performance.json` for counts/warmups and setup.

Real evaluation RSS was about 1.04 GiB with embeddings and 1.90 GiB after the local LLM loaded. The reranker resource check found only 0.96 GiB free, below its 5 GiB guard. BGE was neither loaded nor benchmarked/deployed; there is no judged reranker improvement claim. Transformer retraining was not attempted under these constrained resources. The deployment service's memory/concurrency limits are examples, not measured capacity guarantees.

## 17. Exact changed files

See `PRODUCTION_READINESS_CHANGED_FILES.md` and `results/release-readiness-20261015/changed-files.json`. The manifest compares SHA-256 values against the captured start-of-pass working tree, including initially untracked files. It therefore distinguishes this pass from historical dirty work. Generated logs/checkpoints/screenshots remain ignored. No unrelated reset/restore was performed.

## 18. Tests and acceptance matrix

- Final backend: **1,287 passed, 2 opt-in skipped**, one Starlette/httpx deprecation warning; `backend-release-final.log` (58.06 seconds). The two opt-ins were separately run: **2 passed**, including real isolated-backend browser clarification and synthetic API timing (`opt-in-tests.log`).
- Frontend: **134 passed across seven files** (`frontend/unit-tests-final.log`). Typecheck, lint, format and production build passed. Live application OpenAPI equals the checked-in snapshot. The last backend retrieval change additionally passed 55 targeted tests and the full final suite.
- Production-build browser smoke passed at all three requested widths with synthetic APIs, both languages, generated warnings, Google-only entry, no private local storage, source-back navigation and task-filter restoration. Earlier smoke failures were corrected: an exact select label was added and assertions now wait for filter rendering before subsequent navigation.

| Area | Automated evidence | Missing external/representative evidence |
| --- | --- | --- |
| Auth/session/CSRF/logout/expiry/isolation | Google/browser auth, backend isolation, deployment-security tests | Real deployed Google/TLS/browser session run |
| Inbox filters/pagination/bilingual | API tests, inbox-detail/frontend smoke | Concurrent deployed latency |
| Search Arabic/English/mixed/entities | Semantic API and UI tests | Judged representative retrieval quality |
| Ask facts/travel/paraphrases/entities | Entity/relational/grounding/release tests | Human correctness and wrong-source adjudication |
| Ask existence/time/status/digest | Planner/deeper/release tests and fixed read-only probes | Human relevance/completeness/false-abstention labels |
| Ask ambiguity/follow-up/generated warning | Clarification/browser integration and UI tests | Broader natural conversation coverage |
| Tasks/deadlines/order | Extraction/storage/API tests and 72-case diagnostic | Representative human-reviewed precision/recall |
| Settings/reconnect/sync/OAuth failures | Mocked provider/API and browser tests | Bounded real sync and provider failure recovery |
| Migrations | Isolated backend/semantic/fact migration tests in full suite | Production backup restore and target-host upgrade rehearsal |

Additional public-release gates are deliberately **not marked passed**: human-review at least 200 representative task messages including ≥50 actionable and ≥30 actual deadline cases; task/action precision ≥0.95, recall ≥0.80, correct deadline-association precision ≥0.95/recall ≥0.80. Ask requires ≥200 independently judged representative queries with ≥50 Arabic and ≥50 English, coverage of every supported intent and answerable/ambiguous/unsupported cases; supported-answer correctness ≥0.95, citation correctness ≥0.99, unsupported factual-answer rate ≤0.01, false abstention on answerable queries ≤0.10 and language gap ≤0.05. Counts, denominators and uncertainty must accompany results. These are prospective engineering acceptance targets, not statistics inferred from the small development sets. A separate target-host mixed workload must establish acceptable warm/cold p95 and memory behavior before capacity is advertised.

## 19. Production database modified?

**No, by this pass's database operations.** Mailbox diagnostics used server-enforced READ ONLY transactions and rollback; test writes used the guarded separate test database. No production schema/grant/deletion/model activation was executed.

The production database itself was not static across the multi-day pass: the initial snapshot had 3,912 emails, 456 tasks, 3,912 predictions, 1,581 facts and 5,636 chunks; later snapshots had 3,918 / 459 / 3,918 / 1,590 / 5,647. The source of those intervening changes was not audited and is not attributed here. Full-row hashes match exactly between the isolated pre-optimization and optimized evaluations. It would be false to claim the initial and final mailbox snapshots are identical. Schema observed: `c4d9e6f135ab`; facts version: `facts-v2-relations`; embeddings: `intfloat/multilingual-e5-small`.

## 20. Reprocessing performed?

**No.** No bulk classification, task/fact regeneration, embedding rewrite or migration ran against production. Existing source mail, models and backups were retained. Improved extractor source code is available for review; its diagnostic success does not authorize historical data activation.

## 21. Remaining limitations and next gates

1. Locate and verify the private human review workflow; establish a representative untouched final sample. Freeze the selected classifier and policy before a single final evaluation. Current model quality remains unacceptable for a public accuracy claim.
2. Collect independently judged task and Ask evidence. Review actual absences, source selection, omissions and ambiguous outcomes instead of treating “answered” or “source-supported” as correctness.
3. Implement and validate resumable bounded Gmail sync; measure concurrent Inbox/Search/Ask/sync and cold-start behavior on the target host. Long local-generation fallback remains unresolved.
4. Verify the deployed origin, real login/consent/session lifecycle, operational deletion, restore/rollback, dependency environment and Google public requirements. No checklist completion is assumed.
5. Only after all gates pass: verified backup, recorded manifests/counts, bounded idempotent activation, integrity comparison and tested rollback. Do not activate the experimental sparse models.

## 22. Independent ratings

| Area | Rating | Reason |
| --- | --- | --- |
| Classification | **C — blocked** | No representative human final evidence; no release-qualified replacement for the current model |
| Task extraction | **B — limited beta** | Improved conservative regression behavior; representative precision/recall and stored-data activation missing |
| Ask Mail | **B — limited beta** | Specific bilingual/retrieval improvements verified; judged quality, broad reasoning and latency remain limited |
| Frontend UX | **A — production baseline** | Requested design/flows and responsive production build pass; this does not certify backend intelligence |
| Auth/security | **B — limited beta** | Code-level controls/tests improved; real deployed origin and independent operational validation missing |
| Deployment readiness | **C — blocked** | Unbounded sync, no demonstrated target deployment/restore/capacity and missing Google/public-operation evidence |

## 23. Final release verdict

**Not ready for public release.** The launch blockers are the classifier evidence/quality gap, missing representative task/Ask validation, unbounded sync and unproven operational/Google readiness. Continue only as a controlled limited beta under existing admission restrictions; do not interpret these tests as authorization to publish or bulk-reprocess production data.
