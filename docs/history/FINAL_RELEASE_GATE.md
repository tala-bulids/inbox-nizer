> Historical local development report, preserved from the accessible workspace. Its results are not new verification or a claim of production readiness. See ../../README.md for current setup and ../VALIDATION.md for this update.

# inbox-nizer — final release gate, 17 October 2026

1. **Fixed:** Gmail sync now uses durable checkpoints, bounded batches, resumable source/stage commits, per-account locks and safe History-cursor publication. Recovery covers interrupted work, partial failures, duplicate events, expired page/History cursors and tenant isolation. Long local model computations run outside DB transactions. Settings exposes Continue sync. A real development Ask probe revealed a repeated clarification choice; the response now requests a more specific question instead of repeating the same choice. No frontend redesign or model retraining.

2. **Human review:** Located the existing private classification export: **184 development rows, 0 labelled, 0 reviewers**. Its holdout was not opened. Prepared private task queues (100 development + 100 separate holdout messages) and an Ask development queue (15 probes with actual answers/source evidence); all human judgements remain blank. The Ask holdout is an empty template for independent human questions. See [review instructions](../../RELEASE_HUMAN_REVIEW.md). Exports are Git-ignored; final scoring requires a freeze manifest and an exclusive consumption receipt. Sampling representativeness is not asserted.

3. **Classifier:** Production artifact unchanged. No candidate comparison or final evaluation was run because human development labels do not exist. Classification remains blocked; no new accuracy claim.

4. **Task metrics:** Human-reviewed precision, recall, false positives and deadline-association accuracy are **unavailable**, not zero. The 100 development rows await review. Existing synthetic regression results are not substituted for human evidence.

5. **Ask metrics:** Human answer/source/citation correctness, false abstentions and unsupported-claim rates are **unavailable**. The unjudged probes returned eight answers, five abstentions and two clarification states. These response states are not accuracy. The captured selected-email clarification response predates the small refinement fix; that fix has a focused end-to-end regression test. Observed warm Search: 0.044–0.110 s; warm travel Ask: 2.97–4.61 s; digest: 0.60–1.82 s; local fallback: 24.35 s; first cold travel request: 114.28 s on this workstation while other checks were active. This is not an isolated capacity benchmark.

6. **Gmail sync:** Each request handles at most five source IDs, two listing pages of up to 50 records, five reconciliation deletions and one older enrichment retry. The 20-second budget is soft: one provider/model operation may exceed it. Progress survives restart; Settings continuation is explicit, not an installed background scheduler. Actual PostgreSQL commit/lock behavior is tested with synthetic Gmail/model boundaries. The synthetic 12-message benchmark completed batches of 5/5/2 in 0.52/0.45/0.20 seconds. Synthetic Inbox first-page p50/p95 was 154/258 ms. These exclude real provider/model/network latency and concurrent load. Live Gmail deployment and capacity remain unverified. See [sync operations](../../deploy/BOUNDED_SYNC.md).

7. **Deployment/security:** HTTPS/same-origin `/api`, restricted runtime role, cookies, CSRF, CSP and sanitized logging are retained. New migration `d5ea7f246bc0` is admin-only and **not applied to production**; runtime grants and target-host deployment must precede use of the new sync code. Readiness rejects the old schema. Backup/restore/rollback procedures were reviewed; a real restore and nginx/systemd/TLS restart rehearsal were not executed. The [Google operator register](../../deploy/GOOGLE_PUBLIC_RELEASE.md) records exact callbacks and unresolved external evidence, without claiming approval.

8. **Tests:** Full suites ran once: backend **1,300 passed, 4 failed, 1 skipped**; frontend **134 passed, 1 failed**. The failures were stale migration/sync expectations and a Search cancellation test race. After corrections, affected backend files passed **8/8** and Ask/Search passed **35/35**; the full suites were not repeated. Typecheck, lint, format check, production build and browser smoke checks passed. Browser checks covered Arabic/English at 1440/820/390 px with synthetic APIs: no page errors or overflow. Earlier focused sync/ownership/OAuth, human-review tooling and clarification checks passed. The optional backend browser integration test was skipped. Non-failing dependency deprecation/build-annotation warnings remain. Logs and the pass-specific changed-file manifest are in `results/final-release-gate-20261017/`.

9. **Production data changed? No.** No production migration, sync, deletion, classifier activation or bulk reprocessing ran. Real-mailbox probes were server-enforced read-only; source/derived table hashes match before and after the probe snapshot. Original mailbox export and model artifacts were preserved. No staging, commit, push or unrelated reset/restore.

10. **Remaining external/manual blockers:** Actual human development reviews and representative final quality evidence; selected-model final gate; target-host migration/grants, live Google/bounded-sync and concurrent-load acceptance; verified restore/rollback; actual domain, public homepage/privacy/support/retention/deletion process; applicable Google restricted-scope verification/security-assessment evidence. Cold-start and local fallback latency still need target-host acceptance. Repository tests cannot complete these steps.

11. **Ratings:**

| Area | Rating |
| --- | --- |
| Classification | C — blocked |
| Tasks | B — limited beta |
| Ask Mail | B — limited beta |
| Frontend | A — production baseline |
| Auth/security | B — limited beta |
| Gmail sync | B — tested implementation; live deployment pending |
| Deployment | C — blocked |

12. **NO-GO — NOT READY FOR PUBLIC RELEASE.** The remaining blockers are the human quality gates and the external/operational evidence listed above. No production reprocessing is authorized by this report.
