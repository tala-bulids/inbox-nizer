# Inbox-nizer — project status and V1 release contract

**29 October 2026 — Phase 5 release qualification (not deployed):** Real fresh-process probes measured the unchanged full E5 + selected A stack at **918.21 MiB**, existing FP32 ONNX at **940.32 MiB**, and existing INT8 ONNX at **398.00 MiB**. FP32 preserved all tested rankings; INT8 preserved Recall@5/citation sets but reduced MRR from 0.76190 to 0.72024 and nDCG@5 from 0.69897 to 0.68668. The INT8 adapter remains offline qualification code; no model or quality threshold was silently replaced. A reviewed release factory now rejects private mailbox configuration, pins and hashes E5, warms both models before readiness, and rejects the historical classifier route. Existing local/full behavior remains available. Local checks: 58 showcase tests, 13 ML tests, 185 frontend tests, typecheck/lint/build/API contract and real bilingual desktop/mobile browser flows passed. [Exact evidence, model limits and reproduction](docs/phase5/README.md); [transition requiring explicit approval](deploy/AI_SHOWCASE_RELEASE.md). **PUBLIC AI SHOWCASE: NO-GO** pending a hosting decision, approved private artifact delivery, live-service transition approval and actual target-host/public acceptance. The unchanged runtime cannot fit Free; the smallest listed larger RAM plan is 1 CPU/2 GB at $25/month, not authorized. Render still reports old Gmail source `f53e22c`, auto-deploy off and a migration-on-start command. No private database or production configuration was accessed/changed; no deployment, purchase, credential rotation or retraining occurred. README/Homepage launch claims remain unchanged until live acceptance. Published code/test HEAD **`d7d5712dcb943b16c9900229352ad948f2d305eb`** is verified on GitHub; [CI run 40893033160](https://github.com/tala-bulids/inbox-nizer/actions/runs/40893033160) passed: **1,450 backend tests, 6 skips, 2 passing subtests; 185 frontend tests; pip check, lint, typecheck, API contract and all three builds**. The final follow-up changes only this evidence/documentation and skips redundant CI. Application/test files match the green SHA; no deployment occurred.

**29 October 2026 — Phase 4 interactive portfolio:** Ask Mail, Smart Tasks, Email Collection and Model Lab now form the public showcase navigation. The playground explicitly uses hash-verified Phase 2 research candidate A; historical ONNX/Gmail implementations are preserved. Model Lab reads saved experiments, final losses, class metrics, confusion matrices and calibration; unavailable curves/Arabic/final-test results are labelled honestly. Request-local inputs, bounded inference and a timestamp-only rolling budget are implemented. Real local bilingual desktop/mobile flows and safe screenshots are recorded in [Phase 4 evidence](docs/phase4/README.md). Verified: 185 frontend tests, typecheck/lint/build, 44 backend cases (43 in the final full run plus the unchanged timed-out classifier case passing on isolated retry), and real warm-model browser flows at 1440/390 px. A cold Ask exceeded 120 seconds before recovery; cold-start readiness remains open. This is a local UI/inference implementation, not a quality-gate pass or deployment. Render Free remains blocked by the measured E5 memory requirement. No production data/configuration changed.

**28 October 2026 — Phase 3 local implementation:** The showcase now uses 24 fictional bilingual messages, original-span E5 indexing, deterministic extractive Ask composition, related-thread/cancellation/conflict handling, and task evidence/owners/deadline states. Public Qwen generation is rejected; optional offline/private code is preserved. Real frozen-suite evaluation: Recall@5 0.7619, nDCG@5 0.6990, citation precision 0.9688, evidence sets 18/20; six missing-evidence cases abstained. The 12 labelled task fixtures matched, but the suite is same-author and not an independent quality benchmark. Two failures remain: inclusive reference-day deadline filtering and loss of a positive request sharing a line with a negative instruction. No post-evaluation RAG/task tuning was performed. Checks: 38 backend showcase tests, 180 frontend tests, typecheck/lint/showcase build and real-model bilingual desktop/mobile browser flows passed. E5-only peak process memory was 880.27 MiB; **Render Free remains NO-GO against its 512 MB budget**. [Architecture, benchmark, limitations and exact runtime](docs/phase3/README.md). Independent human QA/task evaluation and hosted resource qualification remain open. No deployment, production/database change or automatic next phase.

**28 October 2026 — Phase 2 research executed:** On the same `codex/ai-showcase-phase1` branch, based on `906e228`, the pinned publisher-MIT synthetic ten-category corpus was prepared with provenance, contact redaction and template-group splitting. A TF-IDF linear model and a frozen multilingual E5 linear head were actually fitted; historical checkpoint-3159 was evaluated without retraining and excluded from selection because of possible source overlap. English validation (215 rows): A accuracy 0.883721 / macro-F1 0.704303; B 0.934884 / 0.726048 (contaminated); C 0.837209 / 0.659110. A is the research selection only. No Arabic labels, representative final test or task labels were admitted; no test predictions were made. Real transformer fine-tuning is **NOT EXECUTED**; its deterministic HF/PyTorch recipe passed tiny random-model tests. Pipeline 13/13, existing training/data 5/5 and showcase 18/18 checks passed. [Full evidence and reproduction](docs/phase2/README.md), [model card](docs/phase2/MODEL_CARD.md), [machine-readable comparison](docs/phase2/evidence/experiment-comparison.json). **V10 remains FAIL; no production model, website, database, hosting or credentials changed. Phase 2 stops here.**

**28 October 2026 — product direction changed by the owner:** Inbox-nizer is now an AI Engineering portfolio application. Phase 1 is developed on `codex/ai-showcase-phase1`, isolated from the preserved release worktree, based on verified `693feb0`. [AI_SHOWCASE_SPEC.md](docs/AI_SHOWCASE_SPEC.md) is the current product scope and acceptance contract for this branch. The earlier Gmail-first scope below is historical/optional; it does not block the database-independent showcase foundation. The classifier quality failures remain factual and are displayed in Model Lab. No deployment or Phase 2 work is authorized or performed by this phase. Future public URL remains `https://inbox-nizer-beta.onrender.com`; no new public site is created.

**Phase 1 verification:** 18 isolated showcase backend tests, 108 existing RAG regressions, 178 full frontend tests (before the final navigation regression), and 6 final focused frontend tests passed. Typecheck, lint, standard/showcase builds and unchanged legacy API contract passed. Real ONNX/E5 inference and anonymous bilingual desktop/mobile browser checks passed locally. [Sanitized evidence](docs/AI_SHOWCASE_PHASE1_EVIDENCE.json). Optional Qwen synthesis quality and target-host capacity remain unverified; V10 still fails. No deployment occurred.

Last audited: **23–24 October 2026**. Code baseline: **`05f452ab0c168c376153f0ddae84b044c73bfb53`**, branch **`codex/inbox-nizer-release`**.

**Public demo launch, 25 October 2026: PUBLIC PORTFOLIO DEMO — GO.** [Open the verified interactive demo](https://inbox-nizer-demo.onrender.com/). Separate Render Static Site `srv-dbeuol4s728c73dh4n5g`, deploy `dep-dbeuolks728c73dh4o8g`, serves exact commit `0d383fea7bd913f63ffe752c22919859d88c39d3`. Anonymous desktop/mobile browser acceptance passed in Arabic and English, including filtering, pagination, detail/tasks, direct refresh and zero account/API/credential access. [Exact evidence](docs/release/PUBLIC_DEMO.md). **FULL GMAIL-CONNECTED PRODUCTION remains NO-GO**; V10 is still FAILED and the private service/database were not changed. This separately authorized isolated demo does not waive any production gate.

**Final portfolio freeze, 25 October 2026:** **PORTFOLIO SOURCE RELEASE: COMPLETE. HOSTED PRODUCTION RELEASE: NO-GO.** This explicitly closes source/portfolio presentation scope, not the unchanged production acceptance gates. The release branch is verified as GitHub's default; the operator confirms the temporary external IP rule was removed and verified. Exposed-credential rotation remains deferred. This final state supersedes earlier candidate/default-branch/IP-rule statements below. See [the final freeze ledger](docs/release/PORTFOLIO_FREEZE.md) for A/B/C dispositions, checks and exact remaining production blockers. No application code or infrastructure changed in this freeze.

**V03/V10 follow-up, 24 October:** the export source has now been identified as `results/checkpoint-3159` (`97a26b67…`), not the separate `email_classifier` directory (`1686c767…`). The prior mismatch interpretation is superseded. Source identity is resolved; release approval and representative quality acceptance remain blocked. See [the focused evidence report](docs/release/V03_V10_EVIDENCE.md) and the final V03/V10 section below. No model was replaced or retrained.

**Closure execution, 24 October:** release HEAD `30d7c357b762ba9305f69acf03ff6105bd639e0d` was published and verified through Git and GitHub. Both remote CI runs passed. This closure change adds documentation and synthetic screenshots only; application code remains `b3225fa`. **NO-GO for hosted V1:** classifier approval/quality, target-host acceptance, isolated restore, database expiry and now-confirmed credential/access cleanup remain open. See the final closure ledger below; historical evidence sections retain their original dates and scope.

**Verify & Deploy preparation, 24 October:** code candidate **`b3225fa0b6e2863aae1c445f1789d3303fabd8e1`** on `codex/inbox-nizer-release`; preparation commits `3405cf0`, `5ed8b46`, `b3225fa` preserve every Stabilize commit. **NO-GO for production.** Live Render remains `f53e22c`; no deployment, migration, configuration or credential changes were made. The current evidence and exact unblock steps are in the final section of this document and [the Render release runbook](deploy/RENDER_RELEASE.md). Earlier audit statements below are historical unless superseded by that evidence.

**Stabilize complete, 24 October:** V05–V09 are implemented in local commits `8037691`, `9c13764`, `3977d52`, `bd45e46`, `0f3b1ee`. Final validation at `0f3b1ee`: **1,370 backend tests passed, 5 opt-in checks skipped, 2 subtests passed; 162 frontend tests passed; lint, typecheck, build and API contract checks passed**. These commits are not pushed or deployed. The audit baseline above remains the reference for before/after findings. That phase ended here; the subsequent user-authorized Verify & Deploy preparation is recorded below.

This is the single source of truth for current product scope, release blockers and remaining work. Historical reports describe their dated experiments, not current release approval. Update this file when a checklist item is verified; include the tested commit, environment and evidence. Do not mark work complete merely because code exists.

**Current verdict:** complete as a technically honest portfolio/source release, suitable for repository review and supervised demonstrations with provisioned prerequisites. It is **not** a turnkey clean-clone deployment or an approved hosted product. Local model artifacts and Google credentials are not distributed. The user-reported 1,585-message Gmail run is integration evidence, not proof that the latest source, classifier or recovery paths are deployed. Classification is experimental/unapproved; V10 remains failed.

**Freeze:** finish the existing organizer. No new AI features, model replacement, broad refactor, new queue infrastructure, paid API, hosting migration or visual redesign belongs in this release.

## 1. Product and bounded V1

Inbox-nizer is a read-only Gmail organizer with an Arabic/English interface. Its core value is turning imported email into a manageable inbox with category and priority suggestions, short extractive summaries and source-linked tasks/deadlines. Suggestions must remain distinguishable from the message text.

The recommended V1 is an **invited-user portfolio beta on the existing Render deployment**, with one connected Gmail account as the supported happy path. Existing ownership supports multiple users and accounts; do not rewrite that model. App sign-in and Gmail consent remain separate. There is no password signup flow, and adding one is unnecessary.

### In V1

- Google application sign-in for allowed users, session restoration and logout.
- Gmail connect/reconnect and an accessible disconnect action using the existing backend endpoint.
- Automatic, bounded recent import; durable continuation; incremental updates; manual **Update now**.
- Inbox, category/priority filters, pagination, email detail, summaries and read-only extracted tasks.
- Existing classifier, provisioned and validated for the hosted runtime; explicit recovery when enrichment fails.
- Existing Arabic/English layout and RTL support. Bilingual UI is **not** a claim of validated Arabic classification accuracy.
- Accurate connection/update states, no duplicate messages, source preservation and a documented data-deletion route.
- A reproducible deployment and a tested, sanitized demonstration.

### Out of hosted V1

Semantic Search and open-ended Ask, multilingual embeddings and Qwen generation are **local/full-runtime features pending separate qualification**. Keep their implementation and tests; remove their unsupported entry points from the hosted V1 and reject direct unsupported API calls before loading models. Do not spend this release building a new model-free search/RAG system to preserve every menu item.

Also deferred: Gmail writes/send/reply, task completion/reminders/calendar integration, attachments, Gmail Push/Pub/Sub, always-on background processing, unrestricted public signup, multi-account UX expansion, model retraining/calibration, a new ranking system, and enterprise-scale operations.

## 2. Repository reality and consolidation boundary

The audit inventoried **300 tracked files**, including **244 Python/TypeScript source and test files** (26,351 lines including generated API types). Python syntax/import relationships, runtime entry points, migrations, frontend routes, deployment examples, quality tooling and tests were inspected. This is a repository audit, not a penetration test or a live infrastructure inspection.

| Checkout | State observed | Disposition |
| --- | --- | --- |
| Release worktree: `private_review/render-sync-fix` | Clean at `05f452a` before this documentation pass; branch `codex/inbox-nizer-release` | Canonical release source. Make release changes here. |
| Original project directory | `frontend-retro-redesign` at `39046c2`, extensive modified/untracked files | Preserve. It contains both already incorporated work and additional candidates; do not run a bulk copy, reset or merge. |
| `private_review/render-release` | `codex/render-free-beta` at `ece81af`, modified/untracked deployment experiments | Preserve as experimental source, not the release target. |

The selected text-file comparison found 200 identical files, 48 differing files and 27 files present only in the release checkout. These counts exclude some file types; they are not counts of independent features still missing.

**Publication gap verified on 24 October:** `git ls-remote --symref origin HEAD refs/heads/main refs/heads/codex/inbox-nizer-release` reports GitHub's default branch as `main` at `88d154e1b919eb52b552fc81c5abf48bd8410520`; the remote release branch is at `05f452ab0c168c376153f0ddae84b044c73bfb53`. Opening the repository's default URL therefore does not show the audited application. Until a separately authorized release/default-branch decision, link reviewers directly to `codex/inbox-nizer-release`. This audit does not merge into or change `main`.

Important differences needing an explicit disposition:

- The experimental checkout has `deploy/render-build.sh`, `render-start.sh`, `requirements-render.txt`, `render_models.py` and `RENDER_FREE.md`. They are **not committed in the release branch**. Reuse only reviewed deployment details compatible with the approved runtime.
- Experimental `onnx_inference.py` implements int8 classifier/embedding session switching. The release instead has `onnx_classifier.py`, preserving FP32 classifier weights with external tensors. These are competing approaches, not two features to combine. Keep the release path; do not silently promote experimental quantization or embedding support.
- The experimental `RAG_GENERATION_ENABLED` guard and presentation changes are absent from the release. Copying that flag alone would not solve the release branch's embedding dependency. Hosted V1 should gate the whole unsupported Search/Ask capability.
- The original workspace has stronger candidate database-role checks in `deployment_health.py` and associated tests. Review those narrowly during the security gate; neither discard them nor assume all original-workspace changes are newer/better.
- `docs/history/legacy-workspace.patch` archives the old accidental `t_gmail.py` diff. It is historical material, not a migration or a script to execute.

The audit baseline `05f452a` was pushed with **`[skip render]`**, but its migration and model artifact were not deployed in the preceding work. Stabilize commits also use that marker and remain local. Do not push an unmarked follow-up commit to an auto-deploying service before those prerequisites are ready. The subsequent read-only Render inventory is recorded below. Live schema, runtime role and connection configuration remain unverified.

## 3. Architecture as implemented

```text
React SPA (session memory, React Query, Arabic/English)
  -> same-origin /api proxy
  -> FastAPI main.py
       -> Google OIDC login -> hashed application session
       -> separate Gmail OAuth -> encrypted refresh credentials
       -> OwnedSession -> PostgreSQL
       -> bounded Gmail sync -> source storage -> staged enrichment
       -> inbox/detail/tasks APIs
       -> optional full-runtime semantic retrieval / grounded Ask

Browser GmailSyncProvider -> serial sync POSTs -> durable DB checkpoint
GmailSyncProvider stops with the browser; PostgreSQL preserves continuation.
```

### Frontend

React 19, TypeScript, Vite, React Router, TanStack Query, Zod, Tailwind, Radix Dialog and Lucide; npm lockfile committed. Node 24 is used by CI and is the straightforward development choice. There is no Next.js or frontend server-side rendering.

`frontend/src/app/App.tsx` mounts authenticated providers around Inbox `/`, Detail `/email/:id`, Search `/search`, Ask `/ask`, Tasks `/tasks`, and Settings `/settings`. `/oauth/complete` is a public callback-result page which navigates successful consent back to the authenticated app. The server reports its runtime profile through the accounts response; `Shell.tsx` hides Search/Ask on Render Free and their direct frontend routes show Not Found. Backend requests are independently rejected before retrieval or inference.

`AuthProvider.tsx` restores the HttpOnly server session, obtains a CSRF token and seeds account state. Production shows Google sign-in; a bearer-token form is development-only. Private query/session state is in memory and cleared on logout. Search/Ask state survives navigation inside the session, not browser restart. `ApiClient` uses same-origin credentials, no-store requests and abort signals; it avoids exposing raw server errors.

Generated OpenAPI types coexist intentionally with Zod adapters for endpoints whose response schemas are untyped. The checked-in OpenAPI snapshot matches the backend at this baseline. Do not remove either layer as alleged duplicate code without replacing its role.

### Backend and API surface

FastAPI is assembled in `main.py`; `routes.py` includes account and Ask routers. Synchronous handlers use SQLAlchemy/PostgreSQL and Google client libraries. There is no worker queue or scheduler. `app.py` is the offline classifier trainer, **not** the HTTP server.

| API group | Current routes / behavior |
| --- | --- |
| Application authentication | `POST /auth/google/login/start`, `GET /auth/google/login/callback`; `GET/DELETE /auth/session`; development-only `POST /auth/session` |
| Gmail consent | `POST /auth/google/start`, `GET /auth/google/callback`; legacy `GET /auth/google` remains |
| Accounts and sync | `GET /gmail/accounts`, `POST /gmail/accounts/{id}/sync`, `DELETE /gmail/accounts/{id}/connection`; legacy single-account `POST /gmail/messages` remains |
| Organizer | `GET /email-categories`, `/emails`, `/emails/{id}`, `/tasks` |
| Enrichment recovery | `POST /emails/{id}/retry-enrichment`; one stored email, shared account advisory lock, no automatic request retries |
| AI utilities | `POST /classify-email`, `GET /search/semantic`, `POST /ask` |
| Operations | `/health/live`, `/health/ready`; `/` returns an API status message, not the SPA |

The frontend expects `/api`; the development proxy strips it. Production must provide an equivalent same-origin proxy, correct callback paths and SPA fallback. The release repository contains nginx/systemd examples; they do **not** prove how the existing Render frontend and backend are connected.

### Authentication and ownership

Google app login validates OIDC claims, state, browser binding, nonce and PKCE. First-time access is restricted by `GOOGLE_LOGIN_ALLOWED_EMAILS` or an existing owned Gmail identity; this is invited access, not general signup. Application sessions are eight-hour, revocable tokens stored as SHA-256 digests, using Secure/HttpOnly/host-only cookies in production. Mutating cookie requests require exact origin and CSRF checks.

Gmail consent separately requests `gmail.readonly`. Refresh credentials and OAuth verifiers are encrypted with versioned MultiFernet keys. Refresh/revocation handling sets reconnect state rather than exposing tokens.

`OwnedSession` applies ownership criteria to mailbox ORM reads and writes, rejects unapproved raw SQL and reassignment, and checks child ownership. This is an **application-level ownership boundary**, not a claim of PostgreSQL row-level-security policies. Authentication and operator sessions are privileged exceptions; they must never replace request-scoped sessions. Runtime database grants are a separate deployment control.

### Database

PostgreSQL, SQLAlchemy 2, psycopg, Alembic and pgvector. Alembic head is **`e6fb80357cd1`**; latest migration adds nullable `gmail_sync_states.import_query` and preserves legacy checkpoints.

| Data | Tables / key guarantees |
| --- | --- |
| Application identity | `app_users`, `app_access_tokens`, `google_identities`, `google_login_attempts` |
| Gmail connection | `gmail_accounts`, `oauth_credentials`, `oauth_attempts`; address uniqueness prevents attaching one address to different app owners |
| Sync continuation | `gmail_sync_states`: mode, generation, anchor/target history IDs, page token, pending IDs, listing completion, fixed import query |
| Source email | `emails`: raw payload, cleaned body, message/parsed dates, Gmail labels, generation; unique `(account_id, message_id)` |
| Derived data | `email_predictions`, `email_tasks`, `email_processing_states`; stage input hash/version/status/attempts |
| Optional retrieval | `email_embedding_chunks` with 384-dimensional vectors/HNSW; `email_facts` with source spans and `email_fact_states` |

Backfills/reprocessing tools use privileged sessions. Several process the entire mailbox or use a single large transaction. They are not HTTP paths and must not be invoked as normal startup/deployment steps.

### Synchronization and enrichment

1. `GmailSyncProvider` runs after authenticated account discovery, on sufficiently stale focus/open and periodically (default 300 seconds). It survives route changes.
2. Requests are serial. Browser Web Locks reduce duplicate tab work; PostgreSQL session advisory locks are authoritative and released in `finally`, with connection invalidation when release/acquisition is uncertain.
3. Each backend batch handles at most five source IDs, two listing pages, limited reconciliation and one prior enrichment retry. A 20-second **soft** deadline is checked between operations; it cannot interrupt an individual slow provider/model operation. Gmail HTTP operations use timeouts.
4. A new import defaults to a fixed 90-day query (`GMAIL_INITIAL_SYNC_DAYS`). Existing checkpoints retain their original query/scope. Zero explicitly selects full mirroring.
5. Once source processing is acknowledged, the stored History cursor enables subsequent `users.history.list` updates. It is not advanced past failed source IDs. Expired History yields a recovery import. Scoped imports do not delete older locally stored archive rows merely because they are outside the window.
6. Source and stage/checkpoint commits preserve resumability. Unique Gmail IDs prevent duplicates on replay. Deleted messages and label changes follow the existing History path.
7. Enrichment stages are clean, classify, extractive summary, tasks, facts, embedding. `full` remains the default. `render-free` uses ONNX classification and marks embeddings skipped/runtime-disabled.
8. `last_synced_at` means successful Gmail contact with committed source progress (or a successful no-change completion), **not** that every old message is imported or every AI stage has succeeded.
9. The frontend caps each continuation run at 30 minutes/1,000 batches, detects repeated progress tokens and backs off errors. After five consecutive unsuccessful runs automatic retries stop for that browser session. Hidden tabs pause after the current batch. Closing every browser stops execution; reopening resumes saved work.
10. Failed source IDs retain attempt counts inside the existing checkpoint JSON. Later pages continue; three automatic attempts exhaust a failed ID until explicit Update now recovery (one bounded batch). Neither History publication nor full-mirror reconciliation discards unresolved IDs. Reopening an exhausted checkpoint does not restart automatic retries. Existing string-only checkpoints remain readable; older code cannot read the new failed-entry metadata.
11. Inbox ordering defaults to parsed `sent_at`, falling back to Gmail `message_at`; unknown dates are last, ties use ID in the selected direction, and filtering precedes pagination. Explicit legacy `created_at` sorting remains supported. Import time is not a fallback message date.
12. Email detail offers a single-request enrichment retry. Completed and runtime-disabled stages stay untouched; failed-stage automatic budgets do not reset. Settings reports failed enrichment separately from Gmail synchronization.

### Classification and other AI

- Ten-label fine-tuned DistilBERT; runtime returns one top label with a raw sigmoid score. It is not calibrated confidence or ten-label UI prediction. Priority is a category/score heuristic, not a learned urgency model.
- `predict.py` selects original Torch inference for `full`, lazy serialized ONNX inference for `render-free`. `onnx_classifier.py` uses exact FP32 exported weights, a reused one-thread session and bounded token input. Artifacts are external, not in Git.
- Summaries are extractive Python rules; tasks, deadlines and structured facts are rule-based. They do not call a paid API or Qwen.
- Full-runtime retrieval uses local multilingual E5-small, pgvector and structured/lexical candidates. Ask can produce deterministic/extractive answers, clarification, abstention, or optional Qwen3-0.6B GGUF synthesis with source validation and an explicit unverified-synthesis warning.
- The extensive `quality/` tooling supports evaluation; it is not proof of real-mailbox quality. Tiny random-model mechanics tests and ten-input export parity probes are not accuracy benchmarks.

### Deployment and dependencies

Core direct Python requirements are pinned, but the main requirements file mixes server, training, test and full-AI dependencies. The optional `requirements-local.txt` points to a **Windows x64** llama-cpp wheel; it is not a Linux/ARM deployment recipe. Runtime memory cannot be inferred from package installation or a successful health probe.

The ONNX export needs offline export-only `onnx` in addition to the trainer dependencies. `deploy/install_classifier.py` can package/install the four runtime files with HTTPS, SHA-256 and archive-content checks. It does not provide an artifact host or choose the approved source checkpoint.

No checked-in Render Blueprint/Dockerfile or validated Render build/start recipe exists on the release branch. Existing systemd memory limits are example host values, not Render Free settings. Preserve the current deployment architecture; capture its actual build/start/proxy and database configuration before changing it.

## 4. Current feature state

“Implemented/tested” below means local code and automated evidence. It does not mean hosted end-to-end acceptance.

| Area | Status | Remaining limit |
| --- | --- | --- |
| Google login, sessions, CSRF, mailbox ownership | Implemented/tested; Google login also user-reported live | Verify deployed origin, grants, proxy headers, account invitation and session behavior |
| Gmail consent, refresh/reconnect/disconnect | Implemented/tested; consent user-reported live | Live acceptance of the Stabilize candidate remains pending |
| Bounded/resumable sync, History and deduplication | Implemented/tested; user reports 1,585 imported messages | Durable failed-source recovery now verified with synthetic Gmail and PostgreSQL; latest candidate is not verified deployed |
| Automatic open/focus/periodic sync | Implemented/tested | Requires an active browser; actual cold starts and multiple-tab behavior need host checks |
| Inbox, detail, filters, priorities, summaries, tasks | Implemented/tested; chronology and explicit enrichment retry fixed | Artifact quality review and remaining onboarding polish |
| ONNX classifier on Render profile | Integration and local parity tested | Approved artifact identity/hosting, Linux memory and live classifications unverified |
| Semantic Search | Implemented/tested in full runtime; disabled at hosted UI/API boundary | Separate future runtime/quality qualification required |
| Ask | Implemented/tested in full runtime; disabled at hosted UI/API boundary | General retrieval/generation remains deferred for hosted V1 |
| Disconnect / deletion | Settings disconnect and retention guidance implemented; operator `delete-user` documented | Live acceptance and operational backup-retention policy remain deployment work |
| Health, CI, operational docs | Implemented locally | Remote CI result, actual host controls, restore drill and release recipe unverified |
| Training and evaluation | Offline training/evaluation path and mechanics tests work | No approved representative quality result established by this audit |

## 5. Problems and work classification

### MUST SHIP — V1 blockers

| ID | Confirmed issue or unknown | Evidence / bounded remedy |
| --- | --- | --- |
| B1 | Release source, public repository entry and deployment are not one reproducible unit | Competing worktrees; build/start/runtime requirements exist only as uncommitted experiments; remote default `main` does not show the release. Selectively reconcile, record actual hosted SHA/config, publish one recipe and point reviewers to the verified release branch. |
| B2 | Resolved locally — hosted capability mismatch | V05 gates navigation, direct frontend routes and backend APIs; no retrieval/model calls on disabled paths. Live candidate acceptance remains separate. |
| B3 | Classification is not yet a qualified hosted feature | New FP32 artifact not provisioned; Linux memory/latency and approved source identity unknown. Readiness intentionally checks no model. Add a release-time artifact/inference check, not heavy inference to health probes. |
| B4 | Resolved locally — import-time inbox ordering | V06 defaults to message chronology with stable ties, missing dates last and tested filtering/pagination. |
| B5 | Resolved locally — exhausted enrichment recovery | V07 adds one-email explicit retries, preserves automatic attempt budgets and separates Gmail update status from enrichment failures. |
| B6 | Resolved locally — source failure blocks later pages | V08 retains failed IDs durably, continues listing, bounds attempts and exposes explicit recovery. Cursor publication still waits for every ID. |
| B7 | Resolved locally — missing disconnect UI | V09 exposes the existing endpoint, explains retained mail/checkpoints and preserves same-account reconnection. Local disconnect does not revoke Google's grant globally. |
| B8 | Deployment security/recovery is unproven | Actual runtime role, owner connection, direct/session pooling, TLS/proxy, limits, logging and backup restoration need evidence. Do not assume nginx examples apply to Render. |
| B9 | Core AI value lacks a bounded representative acceptance review | Existing quality tooling and historical reports are not new approval. Freeze the existing artifact, assess classifications and task/summary usefulness, report supported language/sample limits, and decide once. No automatic retraining project. |
| B10 | Documentation and acceptance evidence contradict the current product | README/frontend README still describe explicitly starting sync; OPERATIONS mentions Continue sync and older schema. Correct current instructions and publish exact verified scope, setup, screenshots and results. |

Security detail for B8: release readiness checks `pg_has_role(..., 'USAGE')` for some owner privileges. That does not test every role a connection could assume. Review effective privilege escalation/`SET ROLE` and privileged membership on the actual PostgreSQL version. The original workspace's stronger candidate checks are worth reviewing, but their mock tests do not prove live grants. PostgreSQL distinguishes these predicates in its [official role-privilege documentation](https://www.postgresql.org/docs/current/functions-info.html).

### SHOULD FIX — bounded polish/reliability, not reasons for another architecture

| ID | Work | Why / stopping point |
| --- | --- | --- |
| S1 | Align remaining onboarding copy | Inbox empty state still directs users to manually sync; connected/no-new-mail and initial-empty states could be clearer. Required retry-state corrections were completed in V07/V08; remaining copy is polish. |
| S2 | Validate numeric runtime configuration once | Invalid `GMAIL_SYNC_INTERVAL_SECONDS`/`GMAIL_INITIAL_SYNC_DAYS` can fail at request time. Reject bad config with a safe actionable startup/release error; no config framework. |
| S3 | Clarify source text terminology | Detail says original stored text but displays cleaned/extracted `email.body`; raw Gmail payload is preserved separately. Label the displayed text accurately; do not build an HTML mail renderer. |
| S4 | Improve OpenAPI response contracts incrementally | Core accounts/sync/emails/search return dictionaries without response models. Zod covers these today; add schemas when touching these endpoints, keeping snapshot parity checked. No API rewrite. |
| S5 | Separate runtime dependencies from training/export/test tooling | Reuse reviewed requirements from the experimental checkout where compatible. Avoid installing Torch merely for ONNX serving; preserve full/local requirements. This can accompany B1, not become a packaging redesign. |
| S6 | De-risk operator scripts | Document which commands are supported, their scope and backup requirement; add bounds/confirmation only for tools needed during this release. Do not rewrite every historical tool. |
| S7 | Add a license decision and contribution/setup clarity | Repository has font licenses but no root application license. Owner must choose terms; do not invent rights to training/model/mail data. |

### LATER — explicitly deferred

- Qualifying embeddings, semantic Search, general grounded Ask and Qwen on a suitable runtime; better Arabic/model accuracy and calibration.
- New training runs, rerankers, new extractors or a large quality-experiment campaign.
- Pub/Sub, schedulers, durable background workers, sync while all browsers are closed.
- Public self-service onboarding and the external Google/public-release process; keep invitation limits explicit in V1.
- Email composing/modification, task editing/completion, calendar/reminders, attachment processing.
- Broader multi-account controls, sophisticated analytics, a redesigned UI, infrastructure migration or framework replacement.

### REMOVE — retire confusion, not working source or user data

| ID | Candidate | Safe disposition |
| --- | --- | --- |
| R1 | Multiple active deployment instructions and competing ONNX approaches | Promote one reviewed recipe; label the rest experimental/history. Do not copy int8 experiments into FP32 release inference. Do not delete dirty worktrees before their owner has a preserved disposition. |
| R2 | `RetroButton`, `RetroInput`, `SourceCard`, `StatusBadge` | No imports from frontend production modules found. Some are used only by component tests. Remove unused wrappers and their tests after a final usage/build check; do not refactor live components to justify keeping them. |
| R3 | Legacy sync/consent aliases and test-only redirect constant | `POST /gmail/messages`, `GET /auth/google`, `gmail_auth.REDIRECT_URI` are absent from current frontend flow or used as test compatibility. Deprecate/document first; remove only after checking external consumers and updating tests. Not a V1 blocker. |
| R4 | Historical reports treated as live release approval | Keep under history with dated labels and links to this file. Drop obsolete quick-start instructions, workstation paths and unsupported “final/ready” claims from active documentation. |

No TODO/FIXME/HACK/XXX markers were found in the scanned source/test files. That does **not** mean the work is finished: the concrete backlog is above. Import inspection found no justification for deleting the RAG modules wholesale; they are connected runtime code, not dead files. Standalone backfill/evaluation CLIs with no inbound imports are also not automatically dead code.

## 6. Intended user journey

1. An invited user opens the HTTPS app; the screen explains that this is an invited beta and what Gmail data is used for.
2. Continue with Google signs into Inbox-nizer. A returning session restores; an uninvited/expired login gets an understandable outcome.
3. First use leads to Settings for separate read-only Gmail consent. After success, the app opens Inbox and starts preparing recent mail automatically.
4. The inbox becomes useful while small batches complete. Existing mail stays readable; categories/summaries/tasks arrive progressively. The user never manages page tokens or batch limits.
5. Opening a message shows its text and clearly labeled suggestions; tasks link back to their source. Date ordering and “last update” mean what their labels say.
6. During normal use, periodic/focus updates fetch changes via History. Update now is optional and quick when there are no changes.
7. Closing/reopening resumes saved progress. Temporary errors back off; exhausted retries expose a recovery action; revoked Gmail consent requests reconnect.
8. Disconnect stops further Gmail access by this app, with retained-data behavior stated. Logout ends the app session. A documented operator process handles data deletion for invited testers.

## 7. FINAL V1 CHECKLIST — dependency order

V05–V09 are implemented and individually tested in Stabilize; their final verification evidence appears below. Other items remain open, including real-host acceptance. This checklist does not authorize deployment or the next phase. Do not expand the release to absorb every SHOULD/LATER item.

| Order | Priority / item | Depends on | Done when |
| --- | --- | --- | --- |
| V01 | DONE — narrow alternate-worktree disposition | This audit | A short include/archive decision exists for the deployment scripts, experimental ONNX/RAG guards and stronger role checks; release source remains on the requested branch, without a bulk merge. |
| V02 | PARTIAL — service/deploy/plan known; live variables/schema/role blocked | V01 | Record service/frontend URLs, deployed SHA/branch, build/start/proxy, runtime profile, DB provider/revision/connection mode and free-plan selection; record secret **names only**. |
| V03 | PROVENANCE VERIFIED; release approval blocked by V10 | V01 | Source checkpoint, tokenizer/config/weight hashes and intended languages are recorded; the ONNX export matches that source and no model is silently promoted. |
| V04 | PREPARED — committed and locally tested; approved artifact/Linux build pending | V02, V03 | Fresh build installs required dependencies and hash-verified artifact; startup performs no training/download/migration; proxy/callback and one-worker settings are reproducible. |
| V05 | DONE locally — gate unsupported hosted Search/Ask paths | Hosted verification remains V02/V17 | `8037691`: navigation/direct routes agree with backend rejection before retrieval; full/local tests preserved. |
| V06 | DONE locally — fix inbox chronological ordering | None | `9c13764`: out-of-import-order dates, missing dates, ties, filters, pagination and legacy sort verified. |
| V07 | DONE locally — make failed enrichment recoverable and status truthful | Actual artifact qualification remains V03/V12 | `3977d52`: exhausted classifier is recoverable through a bounded user action; persisted result, source retention, ownership and retry limits verified. |
| V08 | DONE locally — resolve persistent source-failure recovery | None | `bd45e46`: later pages progress, failures remain durable, retries are capped, reopening does not restart exhausted work, and History advances only after resolution. |
| V09 | DONE locally — expose existing disconnect and retention behavior | None | `0f3b1ee`: Settings disconnect/retention guidance, credential removal, preserved source/checkpoint, same-account reconnect, CSRF/isolation and cascade behavior verified with disposable data. |
| V10 | FAIL — reviewed development reproduced; representative holdout missing | V03 | Freeze one artifact and review a fixed, recorded sample with existing tools. Set acceptance thresholds before scoring, report category/language coverage and task/summary errors; either approve the limited beta or record a specific failed gate. No invented accuracy claim. |
| V11 | PARTIAL — local security tests pass; actual host controls unverified | V02, V04 | Runtime/owner roles and assumable privileges are verified; auth/CSRF/isolation, TLS/cookies, safe logging and request/admission limits work on the actual proxy topology. Document disconnect/deletion and invited access. |
| V12 | BLOCKED — Windows diagnostics only; target Linux access unavailable | V04, V05 | Cold/warm classification, long messages, a five-message sync and concurrent inbox read stay within the actual RAM/admission budget with headroom, no OOM and no ordinary batch exceeding the client's 90-second deadline. Record measurements; Windows RSS is not acceptance. |
| V13 | DONE — local checks and remote backend/frontend CI passed at 30d7c35 | V05–V09 | Targeted regressions then backend/frontend suites, API drift, lint, build and relevant browser smoke pass at one candidate SHA; every skipped check is either executed separately or justified by excluded scope. Remote CI is checked. |
| V14 | BLOCKED — protected live database access/restore evidence unavailable | V02 | A protected backup restores into a separate database; aggregate counts, constraints, schema and credential decryption are checked without exposing data; rollback path is recorded. |
| V15 | MUST — apply the additive migration safely | V13, V14 | Migration owner applies through `e6fb80357cd1`; existing accounts, emails and progress remain intact; restricted runtime readiness passes. No destructive downgrade or mailbox rebuild. |
| V16 | MUST — deploy one pinned candidate | V11–V15 | Actual hosted SHA equals the tested candidate, artifact is verified, correct origin works, health succeeds and a real new email receives a saved category. |
| V17 | MUST — complete live journey/recovery acceptance | V16 | Connect/returning account, multi-page import, usable inbox during sync, refresh/reopen, new-mail History update, no-change update, timestamp, duplicates, token reconnect, disconnect and two-tab cases have recorded results. Use approved test accounts/content only. |
| V18 | PARTIAL — release branch, honest README and sanitized gallery published; verified V1/tag withheld | V10, V17 | README/docs match shipped scope and commands; sanitized screenshots/short demo and limitations are available; a clean clone can follow setup; reviewer links open the verified release branch rather than old default `main`; tag the verified commit and update this file with all evidence. Any merge/default-branch change requires separate authorization. |

For implementation order, V06–V09 can be handled after V01 while deployment inventory is pending. V13 is the final automated check after those fixes, not an instruction to re-run all tests after every documentation edit.

## 8. Setup and deployment notes

- Work from `codex/inbox-nizer-release`; do not run the dirty original checkout assuming it is the release. Keep a single active deployment target.
- Python 3.11 and Node 24 are the tested baseline. Backend entry is `uvicorn main:app`; frontend entry is Vite, with `npm ci` using the lockfile.
- Configure PostgreSQL/pgvector and a distinct `_test` database. `conftest.py` blocks production-engine access in tests. Use a schema owner for migrations and a separate limited runtime role.
- `APP_ENV=production`, exact `BROWSER_ORIGIN`, the two Google callback URIs, `GOOGLE_CLIENT_FILE`, `OAUTH_TOKEN_KEYS`, and invited addresses are required deployment inputs. No secret belongs in `VITE_*`, Git, screenshots or logs.
- Render target profile: `INBOX_RUNTIME_PROFILE=render-free`; default initial window 90 days and interval 300 seconds. Absent profile means `full`, which is not a safe assumption for the small hosted instance.
- Provision `model.onnx`, `weights.bin`, `config.json`, `tokenizer.json` at `CLASSIFIER_ONNX_PATH`. Artifact host/URL and checksum belong in server build configuration. The local test export is not automatically the approved release model.
- Keep PostgreSQL outside ephemeral application storage. Reinstall the fixed model artifact reproducibly during builds. No paid disk/worker/API is required or authorized by this plan.
- Session advisory locks require a direct/session-pooled connection; do not silently switch to transaction pooling. Keep current OAuth and ownership architecture.
- `/health/ready` proves bounded configuration/schema/role checks, **not** model availability or successful Gmail integration. Use a separate release smoke for those.
- Full/local features require E5 cache and, for synthesis, a compatible llama-cpp build plus Qwen GGUF. Do not install the Windows wheel on Render or imply that these features fit the free host.

## 9. README and documentation audit

The README is broadly honest about unverified accuracy/public deployment and correctly describes the classifier CLI, separate login/consent and test isolation. It is not yet an accurate V1 landing page.

This audit adds its link to this status document and corrects the obsolete instruction to explicitly start sync. Before showing the repository as a finished release:

1. Lead with the organizer's user value, supported beta scope, a sanitized screenshot/demo, and access limitations. Move extensive training detail below the application setup or link to model docs; no full rewrite is necessary.
2. Distinguish **hosted V1** from **local/full** Search/Ask/embeddings/Qwen. “Implemented” must not imply all features are available on Render.
3. State automatic sync/active-browser limits, initial window, History updates, truthful last-update semantics and retry/reconnect/disconnect behavior.
4. Document how to obtain/configure the approved classifier artifact; a clone does not contain working weights. Include export-only dependencies and avoid implying training is a prerequisite for trying the product.
5. Publish the actual Render recipe and current migration, not only a generic nginx/systemd host example. Keep all URLs/commands sanitized and current.
6. Update `frontend/README.md` (explicit-click/refresh instructions), `deploy/OPERATIONS.md` (Continue sync and old schema claims), and `docs/MODELS.md` (new ONNX path). They currently disagree with code.
7. Treat `docs/VALIDATION.md` results from 18–19 October as historical. Record newer evidence with commit/environment; do not sum overlapping tests or describe skipped checks as passing.
8. Keep private review CSVs, mailbox exports, model weights and credentials out of publication; clarify data/model rights and add the owner's license decision.
9. Explain that `app.py` trains while `main.py` serves, and that Tasks are extracted/read-only, priority is heuristic and classification scores are uncalibrated.
10. Make the repository entry point match the demonstration: use a direct release-branch link while default `main` remains old. Do not claim this documentation or the current app is visible from the default URL until publication is verified.

## 10. Verification evidence and remaining checks

### Evidence already available

| Check | Result and limitation |
| --- | --- |
| Full backend at `05f452a`, preceding implementation pass | **1,356 passed, 5 skipped, 2 subtests passed**; guarded test DB, not production |
| Full frontend at `05f452a`, preceding implementation pass | **152 passed / 9 files** on final run; an earlier run under concurrent load had timeouts, then passed without assertion/timeout weakening |
| ESLint and production build at `05f452a` | Passed; dependency warnings remain non-fatal |
| Focused recheck in this rescue audit | **95 passed**: isolation, Google login, Render sync, automatic sync and deployment-security tests |
| OpenAPI comparison in this audit | Live application schema equals `frontend/openapi.json` |
| Remote branch check on 24 October | Release branch matches `05f452a`; default `HEAD` points to `main` at `88d154e`. This does not establish remote CI success or the deployed SHA. |
| Fresh `main` import in this audit | No Torch, Transformers, SentenceTransformer, llama-cpp or ONNX Runtime imported; proves lazy startup only |
| Local FP32 export probe from preceding pass | Ten English/Arabic probe labels matched; confidence difference <= 0.0001; Windows backend+inference peak 333.9 MiB. Not Linux qualification or language accuracy |
| Source hygiene in this audit | No tracked `.env`/`credentials.json`/`token.json`; no matches for the limited private-key/GitHub-token/Google-key/Google-secret patterns checked in tracked text. Not a comprehensive secret/history or dependency vulnerability audit |

The prior full-suite skips cover opt-in browser/Ask integration, runtime/batch benchmarks and explicit existing-artifact parity. Choose applicable release checks explicitly. Earlier production-build screenshot tests used synthetic APIs and predate the latest automatic-sync UI.

### Required final verification

- Regressions for B2, B4–B7 and existing full-runtime, tenant/CSRF and advisory-lock tests pass in Stabilize. Repeat the candidate checks if subsequent code changes affect these paths.
- Test a pristine migration chain and upgrade from a populated previous revision with saved sync state. Exercise backup restoration separately from migration tests.
- Assert no heavy imports in **every exposed Render request path**, not only Gmail sync. Test missing/corrupt classifier artifacts at build/release time and prove no request-time downloads.
- Test Gmail 404 History recovery, 429/5xx, invalid/revoked refresh tokens, network loss, malformed/oversized source, DB failure and advisory unlock. Preserve source/cursor invariants.
- Test new account, partial checkpoint, no-new-mail, multiple pages/tabs, failed-stage retry, disconnect, route navigation and refresh/logout in the browser. Repeat RTL/LTR mobile/desktop smoke without changing visual identity.
- Run the full suites, lint, build, API drift and clean dependency installation at the candidate SHA; inspect remote CI. Audit dependency advisories separately before making a security claim.
- Execute the real Render acceptance sequence in V17; record deployed SHA, timings, peak RSS, aggregate counts and duplicate checks without logging private email content.

## 11. Definition of Done and stop rule

V1 is done when **V01–V18 are checked with evidence**, the supported invited-user journey works from a fresh/returning browser on the deployed candidate, new messages are classified without manual batch work, failures are bounded and recoverable, dates/status are truthful, source data stays intact, and unsupported capabilities cannot mislead users or load expensive models on the hosted profile.

The same candidate must pass automated tests and actual host capacity/security/restore/acceptance checks. A new contributor must be able to reproduce setup from the repository, and a recruiter must see an honest demonstration with no private data or unsupported quality claim.

Once those conditions hold, tag V1 and stop. SHOULD FIX items may remain explicitly documented; LATER items do not delay V1. Reopen scope only for a verified blocker in the supported journey. Do not restart development because another AI feature or cleaner abstraction is possible.

## Stabilize implementation evidence (24 October 2026)

V05 implemented locally: backend-owned runtime profile hides Search/Ask navigation and blocks direct frontend routes; backend rejects both APIs with `runtime_disabled` before retrieval/model work. Full/local paths remain intact. Regression-first backend run: 4 expected failures. After fix: hosted capability + Render sync tests **22 passed**; frontend capability + full Search/Ask tests **37 passed**. Frontend required execution outside the Windows sandbox because esbuild could not traverse parent directories. No deployment performed. Subsequent items are individually verified below.

V06 implemented: default `message_date` sorts by `COALESCE(sent_at, message_at)`, unknown dates last in either direction and ID ties matching direction. Filtering precedes pagination; explicit `created_at`/priority/ID options remain compatible. Backend date regressions failed before the fix; inbox suite **32 passed** after it. Frontend inbox/detail suite **18 passed** (an existing navigation assertion was corrected to await the detail page rather than matching the outgoing inbox). OpenAPI and generated types updated.

V07 implemented: `POST /emails/{id}/retry-enrichment` attempts one stored email, shares the account advisory lock, preserves source data, skips completed/runtime-disabled stages and does not reset automatic attempt counters. Automatic processing now respects an exhausted stage even if another stage is pending. Detail exposes an explicit retry; Settings reports failed enrichment separately from Gmail update success. Regression-first test failed on missing recovery state. Final targeted backend **34 passed, 1 skipped** (opt-in batch latency); frontend detail/Settings **50 passed**. Repaired classification persistence, exhausted retries, no automatic retry loop, and cross-owner denial verified. OpenAPI/types regenerated.

V08 implemented: failed source IDs and attempt counts remain in the existing checkpoint JSON; legacy string IDs remain readable. Listing proceeds past failed bodies, successful source records remain intact, and History publication/reconciliation waits until every ID resolves. Three automatic attempts per failed ID; explicit Update now permits one bounded retry batch (at most five IDs), without resetting counters. Reloading exhausted checkpoints does not restart auto retries. Partial work is never displayed as complete. Backend regressions first reproduced the stall; final affected suites **81 passed, 1 skipped** (opt-in latency). Frontend sync/automatic/Settings suites **43 passed**, including later-page continuation, bounded manual retries and reopening. No schema change or live migration. Operational compatibility: older code does not understand failure metadata in pending JSON; do not downgrade an active checkpoint to the pre-Stabilize reader.

V09 implemented: Settings calls the existing disconnect API with duplicate/busy guards, immediately updates connection state and keeps saved Inbox data usable. Retention and same-address reconnection are explained; operator deletion scope is documented in deploy/OPERATIONS.md. UI regressions failed before implementation. Backend disconnect/reconnect, browser CSRF, ownership and OAuth suites **62 passed**; frontend Settings/automatic sync/browser authentication **55 passed**. Tests confirm credential removal, preserved account/source/checkpoint, no Gmail client while disconnected, same-account consent restoration, resumed sync without duplicates and rejected unauthorized mutations. No production data or credentials were modified.

### Final Stabilize acceptance

Code candidate: `0f3b1eeec7c8db78beb87a442ad45ce0bc42dd3c` on `codex/inbox-nizer-release`. Documentation-only reconciliation follows this candidate; runtime code is unchanged by that final documentation commit.

| Check | Exact final result |
| --- | --- |
| `python -m pytest -q --tb=short -ra --basetemp private_review/pytest-stabilize-full` | **1,370 passed, 5 skipped, 2 subtests passed**, 80.44 seconds; 2 dependency warnings |
| `npm test` | **162 passed, 10 test files passed**, 92.06 seconds |
| `npm run lint` | Passed, exit 0 |
| `npm run typecheck` | Passed, exit 0 |
| `npm run build` | TypeScript + Vite production build passed, exit 0 |
| Application `app.openapi()` compared to `frontend/openapi.json` | Exact equality |
| `npm run api:generate` followed by `git diff --exit-code -- src/api/generated/schema.d.ts` | Passed; generated types have no drift |
| `git diff --check` | Passed |

The backend skipped checks are unchanged opt-ins: classifier-review browser smoke, full-runtime Ask browser integration, existing ONNX artifact parity, runtime performance benchmark, and bounded-sync latency benchmark. The first two concern unchanged/deferred tools; artifact and target-host performance qualification remain V03/V12 and are not asserted by synthetic Stabilize tests. Local auth/ownership, CSRF, OAuth callback, real PostgreSQL persistence and advisory locks were exercised; Google network boundaries and classifier failures/results were synthetic. No real Google consent or hosted acceptance was performed in this phase. Live host/CI verification remains a later release gate because these commits were deliberately not pushed or deployed.

Non-failing warnings: google-api-core's future Python 3.11 support notice, Starlette's httpx deprecation, and Rollup dropping two misplaced dependency comment annotations. No dependency replacements were made.

**Stabilize is complete.** No outstanding failed automated check. No schema change, live migration, production data mutation, Render configuration change, merge into `main`, push or deployment occurred. Other worktrees were not edited. Do not continue to the next phase without a new instruction.

### Stabilize file-by-file change record

Paths below are relative to the canonical release checkout. Tests, generated contracts and the prior audit documents account for much of the diff; no dependencies or model implementations were replaced.

| File | Reason |
| --- | --- |
| `PROJECT_STATUS.md` | Commit the audit contract, resolve V05–V09 findings and record exact verification/remaining release limits. |
| `README.md` | Commit the prior audit's status link and corrected automatic-sync setup instructions. |
| `runtime_capabilities.py` | Central server-owned profile check and early unsupported-capability rejection. |
| `routes.py` | Gate semantic search, order inbox by message dates, expose one-email enrichment retry. |
| `rag_api.py` | Reject hosted Ask before retrieval/inference. |
| `account_routes.py` | Publish runtime/recovery counts, compute actionable pending state, accept explicit bounded source retry. |
| `email_pipeline.py` | Respect exhausted stage budgets; permit an explicit one-pass retry without resetting counts. |
| `gmail_sync.py` | Share account locking for enrichment recovery; retain failed source IDs/counts while later pages progress. |
| `frontend/src/app/capabilities.ts` | Read backend runtime capability from authenticated accounts data. |
| `frontend/src/app/App.tsx` | Block direct hosted Search/Ask routes. |
| `frontend/src/components/layout/Shell.tsx` | Hide unsupported hosted navigation. |
| `frontend/src/api/contracts.ts` | Parse runtime profile and durable recovery counts/flags. |
| `frontend/src/api/accounts.ts` | Wire disconnect and explicit source retry; continue later pages despite durably retained failures. |
| `frontend/src/api/emails.ts` | Add bounded explicit enrichment-retry request. |
| `frontend/src/features/inbox/inboxState.ts` | Use message chronology by default while retaining explicit legacy sorts. |
| `frontend/src/features/email/EmailPage.tsx` | Expose one-email retry with pending/error handling and refresh saved results. |
| `frontend/src/features/settings/GmailSync.tsx` | Stop exhausted auto-retries on reopen; permit bounded manual recovery and truthful paused wording. |
| `frontend/src/features/settings/SettingsPage.tsx` | Show source/enrichment recovery separately, expose disconnect and explain retention/reconnect. |
| `frontend/openapi.json` | Refresh actual backend contract for new retry route/query and sort option. |
| `frontend/src/api/generated/schema.d.ts` | Regenerate types from that contract. |
| `test_hosted_capabilities.py` | Verify early Render rejection, no retrieval/heavy imports, and preserved full defaults. |
| `test_inbox_api.py` | Verify out-of-order import dates, missing dates, ties, filtering and pagination. |
| `test_enrichment_recovery.py` | Verify exhaustion, explicit repair persistence, source retention and cross-owner denial. |
| `test_source_recovery.py` | Verify later pages, durable failures, exhausted/reopened state, bounded explicit retry, expired page recovery and cursor safety. |
| `test_disconnect_recovery.py` | Verify disconnect through consent/reconnect to resumed sync, retaining source/account/checkpoint. |
| `test_browser_auth.py` | Extend existing CSRF regression to disconnect and enrichment retry. |
| `test_gmail_automatic.py` | Assert durable failure metadata rather than the old uncounted failed ID. |
| `test_render_sync.py` | Update simulated SQL-failure callback for the explicit-retry argument; retain real lock cleanup assertions. |
| `frontend/src/test/hosted-capabilities.test.tsx` | Verify hidden navigation and blocked direct hosted routes. |
| `frontend/src/test/inbox-detail.test.tsx` | Verify message ordering and failed-enrichment retry/error UI; await detail navigation reliably. |
| `frontend/src/test/sync-run.test.ts` | Verify continuation past retained failures and one manual retry batch. |
| `frontend/src/test/auto-gmail.test.tsx` | Verify exhausted checkpoints stay stopped on reopen and disconnected accounts never auto-sync. |
| `frontend/src/test/tasks-settings.test.tsx` | Verify disconnect/reconnect/retained Inbox, failed disconnect and accurate recovery wording. |
| `deploy/OPERATIONS.md` | Document existing disconnect, retention, reconnection and operator deletion scope; no host configuration changes. |


## Verify & Deploy evidence — 24 October 2026

### Candidate, source consolidation and hosting

Code/test candidate: `b3225fa0b6e2863aae1c445f1789d3303fabd8e1`. This report's
subsequent commit changes documentation only. Branch remains
`codex/inbox-nizer-release`; no reset, main merge, model replacement or bulk
worktree merge. Original and experimental dirty worktrees were not edited.

- `3405cf0`: narrowly adopted stronger readiness checks from the original worktree.
  Owner and admin role membership is rejected even when NOINHERIT hides immediate
  privileges; database/schema/table ownership and DDL checks remain read-only.
  This is conservative and may reject roles with unusable memberships. It does
  not claim PostgreSQL RLS or verify the actual hosted runtime role.
- `5ed8b46`: committed the existing one-process SPA + `/api` topology as
  `deploy/render_app.py`, build/start scripts, serving-only direct requirements
  and 63 transitive constraints. Build checks reject heavy packages and smoke
  the provisioned ONNX artifact offline. Startup requires production settings,
  uses one worker, suppresses access logs and performs no migration/download.
  Added a finite, text-free diagnostic report tool. Public example labels now
  import the shared contract directly, avoiding an unnecessary sklearn import.
- `b3225fa`: corrected outdated browser test expectations for Update now,
  disconnect/reconnect and successful OAuth redirect; added the hosted profile
  browser flow. No frontend product code or design changed in this phase.

Experimental int8 classifier/embedding loading, render_models.py, independent
API-only start command, RAG feature flag and presentation changes remain excluded.
Existing full-runtime and training dependencies are unchanged. No checkpoint,
artifact, Gmail source, OAuth credential or saved continuation was overwritten.

User-confirmed read-only workspace: **Tala's workspace**, `tea-d5domjogjchc73dquke0`.
Service `srv-dbcqvja9lscs73er2pu0` is Python/Free/Frankfurt, one instance, repository
release branch, auto-deploy off, no health-check path. Live deploy
`dep-dbdg1abncjis73a2vvg0` runs **`f53e22cd3c4a881671e06ab6a00b3bd2b9d393c0`**.
Its build generates a wrapper serving the SPA and mounted API on
`https://inbox-nizer-beta.onrender.com`; startup still automatically migrates.
The proposed replacement in the runbook has **not** been applied.

Database `dpg-dbcquaa9lscs73eqtki0-a` is Free PostgreSQL 18 in Frankfurt, with no
managed pool/replicas/HA and no allowed external IPs. Render reports expiration
**21 November 2026 at 06:37:29 UTC**. Durable zero-cost operation is unresolved.
Hosted MCP's read-only SQL query was blocked by that access policy; we did not
open the firewall. The app's actual role, revision, connection/session affinity,
counts, credential decryptability and backup capability remain unknown.

Required variable **names** and exact proposed build/start/health commands are
listed in `deploy/RENDER_RELEASE.md`; live values/names were not inspected because
no read-environment MCP operation was available. Browser fallback failed to
initialize (local CUA kernel assets unavailable). No secret values were printed.
Public HTTPS requests to `/`, `/api/health/live`, `/api/health/ready` and
`/api/auth/session` each timed out from this workstation after 35 seconds;
this is an inconclusive network observation, not proof of an application outage.
Render memory/latency metrics returned no samples. Actual TLS/cookies/proxy trust,
request admission and platform logging still require hosted evidence.

### Artifact identity and finite quality result

**Historical observation, superseded for source identity:** the V03/V10 follow-up below identifies checkpoint-3159 as the exact export source. The `1686c767…` comparison used a different directory; it did not establish that checkpoint-3159 had changed.

Existing `private_review/gmail-classifier-export` is FP32 with external weights.
Its recorded source safetensors SHA-256 starts `97a26b67`; the current local source
checkpoint hash is **`1686c767582eab051298eb82fa048822b9c6142842f61b3a384f55e204f6902b`**.
Config source hash still matches, but weights do not. The historical 19 October
report says `selected_release_model: null`, `decision: BLOCKED`, and final holdout
not ready. No model was silently approved, repacked, uploaded, activated or trained.
The user was asked to identify the approved existing checkpoint; unresolved here.

The existing export passed its ten-reference top-label/confidence parity check
(tolerance 0.0001), session reuse and long-input test in the isolated serving
runtime. This demonstrates parity with its saved references, **not with the
changed current source checkpoint**. The source mismatch remains a release blocker.
Runtime file hashes and diagnostic output are recorded in
[the sanitized artifact evidence](docs/release/verify-20261024-classifier.json).

Predefined classifier-release-v1 acceptance remains >=300 human-reviewed examples,
>=20/class, >=50/language, accuracy >=90%, macro-F1 >=85%, and existing per-class,
Finance, calibration, ambiguity and language-gap limits. No threshold was weakened.
Status mode inspected 100 development review attestations, found no holdout in that
review directory, and returned **failed, rating C: representative human-reviewed
final holdout evaluation missing**. It did not open or consume a final holdout.

Finite public diagnostic: **20 examples**, ten English and ten Arabic, one per
language/category; **English 7/10 (70%), Arabic 1/10 (10%), combined 8/20 (40%)**.
These are tiny synthetic diagnostics, not representative mailbox accuracy. They
provide no basis for an Arabic quality claim. Task/summary regressions passed in
the suite; a representative core-quality review is still missing. We did not select
another model or retrain to improve these scores.

### Performance evidence and limitations

Windows 3.11.9, existing FP32 export, fresh isolated process: cold classification
**0.398 s**, warm p95 **0.053 s** (20 examples), long-input p95 **0.649 s** (10 calls,
2,000 synthetic words each). Fixed diagnostic limits were cold <=10 s, warm p95
<=1 s, long p95 <=2 s, classifier process peak <=384 MiB. Windows memory was
intentionally not recorded by the Linux RSS probe; its performance gate is false.
No Linux distro was listed by WSL; no target Linux execution access was available.
These timings are **not V12 acceptance** or whole-service memory/concurrency proof.

Additional opt-in tests used guarded isolated PostgreSQL and synthetic providers:
- Server-only login p95 21.155 ms (20 samples), session restore 5.979 ms (30).
- Inbox first/later pages p95 24.009 / 32.770 ms (30 each), Tasks 46.386 ms (30).
- No-change incremental sync p95 40.308 ms (30), with mocked Gmail history.
- Bounded import: 12 synthetic messages over **5 + 5 + 2** requests, taking
  **0.5465 / 0.4637 / 0.2742 seconds**, final has_more=false.
No Google network, real provider failures, whole-server model memory, TLS or
concurrent inbox workload is measured by those tests. Target Linux mixed-load
qualification and the client's 90-second request budget remain open gates.

### Automated verification

The final candidate's application changes passed these checks; docs-only updates
follow. Python was 3.11.9, Node 24.11.1. Test DB guards blocked production access.

| Command/check | Result |
| --- | --- |
| Targeted wrapper/security/hosted-capability/Render-sync pytest | **48 passed**, 3.52 s |
| Full backend `python -m pytest -q --tb=short -ra --basetemp private_review/pytest-verify-final` | **1,380 passed, 5 skipped, 2 subtests passed**, 64.01 s (final rerun at b3225fa; initial run 107.61 s) |
| Isolated serving environment, same targeted tests plus `test_onnx_classifier.py` with explicit export | **49 passed**, 4.20 s; parity/long input/session reuse included |
| `test_quality_data.py test_quality_regressions.py test_classifier_release.py` | **115 passed**, 14.89 s |
| Opt-in `test_runtime_performance.py` | **1 passed**, 5.91 s |
| Opt-in `test_sync_batches.py::test_bounded_batch_measurement` | **1 passed**, 1.47 s |
| `npm test` | **162 passed, 10 files**, 140.99 s |
| `npm run lint`, `npm run typecheck`, `npm run build` | Passed; lint repeated after browser-script edits |
| `npm run api:generate` + generated-schema git diff | Passed, no drift |
| Isolated runtime `main.app.openapi()` vs frontend snapshot | Exact equality |
| Isolated serving dependency install, `pip check`, offline classifier smoke | Passed; no Torch/Transformers/SentenceTransformer/llama-cpp installed |
| Isolated real wrapper requests with synthetic auth and DB connection blocker | Liveness/categories/SPA pass; Search/Ask reject 403 without heavy imports |
| `UI_BROWSER_AUTH=1 npm run ui:check` against production SPA through new wrapper | Passed at **1440, 820, 390 px**, Arabic/English, no overflow/page errors, empty private browser storage |
| `node scripts/check-hosted.mjs` against same wrapper | Passed at **1440, 390 px**: one click, 3 pages / 15 messages, timestamp change, reload, retained messages, disconnect/reconnect, direct Search/Ask rejection |
| Bash syntax for both scripts; `git diff --check` | Passed |

The browser APIs/Google redirects were synthetic; live DB access was blocked.
Browser evidence does not claim real consent, Gmail sync or production acceptance.
The full-suite skips were artifact parity and two benchmarks (executed separately
above), plus the offline classifier-review UI and full-runtime Ask browser integration
(outside hosted V1). Full-runtime SPA visual behavior was nevertheless smoke-tested.
Remote CI for this unpushed candidate remains unverified.

Resolved verification failures are retained here: default pytest temp-directory
access denied (workspace-local basetemp fixed it); the development environment
lacked ONNX Runtime (parity passed in the dedicated serving environment); diagnostic
examples initially imported sklearn transitively (now import the same LABELS from
the lightweight contract); exploratory mounted API checks lacked synthetic auth
(corrected without relaxing production auth); browser smoke initially used obsolete
sync/reconnect/callback expectations (updated and passed). No production behavior
was changed to satisfy obsolete test wording. Non-failing dependency warnings:
google-api-core Python 3.11 future support, Starlette/httpx deprecation, two Rollup
comment annotations. No comprehensive dependency-advisory audit is claimed.

### Database recovery, decision and exact unblock sequence

**V14 is NOT passed.** No live dump, restore, schema inspection, row-count comparison,
constraint validation or credential-decryption validation could be performed with
the available access. Local migration tests passing is not restoration evidence.
The runbook now specifies protected PostgreSQL 18 dump/restore commands, separate
isolated target checks, count/constraint/key validation and owner-only additive
migration to `e6fb80357cd1`. Nothing was executed against the real database.

The old live f53e22c code must not be restarted against pending checkpoint objects
written by Stabilize (`{id, attempts}`). Keep a compatible forward-fix path; otherwise
an explicitly approved rollback needs the verified pre-activation database/key/code
snapshot together in an isolated replacement, with post-snapshot-write loss addressed.
Never erase failed IDs or advance History cursors as a rollback shortcut.

**NO-GO for production and V1 completion.** Finite remaining gates:
1. Identify the approved existing checkpoint; reconcile its exact config/tokenizer/
   weights with a parity-verified FP32 export and protected bundle checksum. The
   missing model approval is not permission to choose an experiment.
2. Supply a genuine representative human-reviewed holdout under the unchanged
   quality policy; freeze the approved artifact and evaluate once. Record an
   honest failed gate if it misses criteria. No retraining is authorized here.
3. Resolve Free Postgres expiration before claiming a durable beta. The current
   zero-cost/no-hosting-migration contract does not authorize a paid upgrade or
   new provider; an operator decision is required, with protected backup first.
4. Provide an approved database access path and protected keys to the operator;
   inspect schema/runtime role/session-affinity and perform the isolated restore
   rehearsal in the runbook. Do not expose the DB publicly to unblock hosted MCP.
5. Obtain target Linux execution/access and privately inspect required live variable
   names/settings; qualify full-process memory, cold/warm/long inference, five-message
   sync plus concurrent inbox, proxy/TLS/cookies/logging/admission behavior. Public
   probes/empty metrics in this session were insufficient.
6. Publish the exact candidate to the authorized release branch when ready, inspect
   its remote CI, then present the exact migration/configuration/deploy actions,
   immutable artifact and verified backup identity for explicit user approval.
7. Only after that approval execute activation, actual invited-user hosted acceptance
   and bounded portfolio publication. Do not merge main/change default branch.

The existing running deployment and all source/stored user data were left untouched.
No paid resource, live migration, credential rotation, push or deployment occurred.
Stop here at the access/evidence boundary; do not treat local preparation as V1 done.


## Final V1 closure ledger — 24 October 2026

### Repository and automated checks

Started clean on `codex/inbox-nizer-release` at **30d7c357b762ba9305f69acf03ff6105bd639e0d**.
All ten Stabilize/preparation commits are preserved above 05f452a, including b3225fa
and 30d7c35. The prior publication used a normal fast-forward push; canonical GitHub
and origin both returned that exact HEAD. Origin's historical repository URL redirects
to tala-bulids/inbox-nizer; no remote/default-branch change was necessary.

The previous outgoing-history scan inspected 74 blob versions across those ten
commits, found no credential patterns, private mailbox dumps or model binaries,
and found only synthetic example addresses. The largest outgoing blob was 67,604
bytes. It was not repeated as a new project audit. Closure publication reviews only
the new documentation/gallery delta. The archive/passphrase/credentials are excluded.

Both GitHub Actions runs completed **success** for 30d7c35:
- [40102885080](https://github.com/tala-bulids/inbox-nizer/actions/runs/40102885080)
- [40102881362](https://github.com/tala-bulids/inbox-nizer/actions/runs/40102881362)

Verified backend job steps: CPU dependency installation, full requirements, pip check,
pytest and classifier-review unittest. Verified frontend steps: clean npm install,
API generation/no drift, typecheck, lint, tests and production build. These were
Ubuntu CI jobs, not measurements of the Render allocation or production database.
The exact local final counts remain **1,380 backend passed / 5 skipped / 2 subtests**,
**162 frontend passed**, **49 isolated-runtime/parity passed**, **115 quality
regressions passed**, and one passing test for each optional local benchmark.
The full-suite skipped artifact and benchmark checks were executed separately;
the classifier-review UI and full-runtime Ask browser opt-ins remain outside hosted V1.
No application code changed after the verified candidate; redundant local suites
were not rerun for prose/images. Remote CI for the closure documentation commit
must be read after publication, not inferred from the earlier runs.

### Exact V01–V18 disposition

| Item | Closure status | Evidence or remaining gate |
| --- | --- | --- |
| V01 | COMPLETE | Narrow source disposition; no bulk merge; 3405cf0 / 5ed8b46. |
| V02 | PARTIAL | Live service/SHA/plan/topology and current IP rule known; actual runtime configuration, schema/role/session-affinity still unverified. |
| V03 | PROVENANCE VERIFIED; APPROVAL BLOCKED | Follow-up identifies checkpoint-3159 (97a26b67) as the exact export source. The 1686c767 file is a different checkpoint. No V1 quality approval exists. |
| V04 | PREPARED, NOT CLOSED | Committed same-origin recipe, pinned serving dependencies and offline smoke; approved artifact and fresh target build remain prerequisites. |
| V05 | COMPLETE IN SOURCE | 8037691; hosted UI/API capability gates and no-heavy-load regressions pass. |
| V06 | COMPLETE IN SOURCE | 9c13764; message chronology, ties, missing dates and pagination regressions pass. |
| V07 | COMPLETE IN SOURCE | 3977d52; bounded explicit enrichment repair persists results; ownership/source retained. |
| V08 | COMPLETE IN SOURCE | bd45e46; durable failed IDs, later-page progress, retry bounds and History invariants tested. |
| V09 | COMPLETE IN SOURCE | 0f3b1ee; disconnect/reconnect, retained data, CSRF and ownership tested. |
| V10 | FAILED RELEASE GATE | Follow-up reproduces 32/100 on reviewed development; representative final holdout absent; thresholds unchanged. |
| V11 | PARTIAL / SECURITY ACTION OPEN | Local tests pass; operator reports exposed DB password; temporary laptop rule still present; live controls not accepted. |
| V12 | BLOCKED | Windows diagnostic/Ubuntu CI are not target Render capacity; metrics empty, no target mixed-load result. |
| V13 | COMPLETE FOR CODE CANDIDATE | Full local evidence plus successful remote backend/frontend CI at 30d7c35; closure docs/images are separately checked. |
| V14 | PARTIAL, RESTORE UNVERIFIED | Operator-reported encrypted backup checks pass; no isolated restore/count/constraint/key validation. |
| V15 | NOT EXECUTED | Live additive migration requires restore evidence and explicit approval. |
| V16 | NOT EXECUTED | Live f53e22c is unchanged; no production deployment approved/executed. |
| V17 | NOT EXECUTED | Real invited-user hosted acceptance requires the approved deployment. |
| V18 | PARTIAL | Branch, installation guide, architecture, limitations and sanitized gallery prepared/published; release tag and V1-complete claim withheld. |

Thus the closed checklist items are **V01, V05, V06, V07, V08, V09 and V13**, with
source completion distinct from hosted acceptance. No other gate is checked merely
because a recipe, backup archive, screenshot or passing unit test exists.

### Classifier and quality verdict

**Historical closure verdict:** the source-mismatch claim in the following paragraph is superseded by the V03/V10 follow-up. Its lack-of-approval and failed-quality conclusions still apply.

The prior artifact hashes/parity results remain the evidence of record. No new model
approval or provenance reconciliation was supplied in this closure turn. The existing
export matches its saved ten-reference outputs, not the changed current source.
The source-weight mismatch and missing approval remain unresolved. No retraining,
re-export, model substitution, repeated holdout use or threshold reduction occurred.

The existing finite 20-example synthetic diagnostic remains **7/10 English, 1/10
Arabic, 8/20 total**. This is not representative accuracy. The release policy still
requires >=300 reviewed examples, >=20 per class, >=50 per language and its original
quality/calibration constraints. Status inspection found 100 development attestations
but no representative final holdout in the inspected directory. **Quality is not approved.**

### Encrypted backup evidence and database security verdict

The operator provided this evidence; the agent did not repeat completed verification,
request a passphrase, inspect private mailbox content or assume access to Windows D:.

- Local encrypted archive name: `inbox-nizer-20261024-170201-bb51b442.dump.gpg`.
- Reported encryption: **GPG AES256**.
- Reported SHA-256: **49b141a24d7dae46039e15888a1cd76509a948e6ad43a498f0fece8ebe27d191**.
- Reported verification: **CHECKSUM OK**, **BACKUP DECRYPTION VERIFIED**,
  **POSTGRESQL ARCHIVE LIST OK**, **242 archive entries**, **16 TABLE DATA entries**.
- Reported script names: verify_backup.py and check_inbox_nizer_archive.py.
  No separate verification manifest is confirmed.
- **No full isolated restore has been tested.** Archive listing/decryption does not
  prove restored schema, counts, uniqueness/FKs, checkpoints, application credential
  decryption or recovery time. No archive, encryption key or secret is published.

The operator reports a database password exposed in an earlier screenshot for role
`inboxnizer_beta_db_user`. Flag it for coordinated rotation; no password is reproduced
and no rotation is claimed. Preserve OAuth keys and backup passphrase independently.

A new read-only Render recheck found **one /32 rule labelled Temporary laptop backup
still present**. Earlier empty-allowlist observations are historical and do not prove
current cleanup. **Temporary external access removal is NOT verified.** No rule was
changed without approval. The exact proposed removal and coordinated role-password /
client-config cutover, risks and verification are in deploy/RENDER_RELEASE.md. The
available MCP interface does not expose those Postgres mutations in this session.

### Render and portfolio verdict

Read-only closure checks: live commit still f53e22cd3c4a881671e06ab6a00b3bd2b9d393c0;
auto-deploy remains off. Database remains Free PostgreSQL 18 with reported expiration
**21 November 2026, 06:37:29 UTC**. Memory/limit/latency metrics returned empty series.
Unauthenticated HTTPS checks for root, health/live and auth/session timed out after
about 30 seconds from this workstation. This is inconclusive reachability evidence,
not proof of adequate security/capacity and not a diagnosis of service failure.

README now leads with the actual product, source-vs-hosted status, runtime capability
table, architecture, install prerequisites and known limitations. New portfolio
screenshots show the existing built UI with **render-free** capability fixtures:
Arabic/English desktop Inbox and mobile Settings. All senders are example.invalid;
all content/classifications/summaries/connection state are synthetic. External browser
requests and local database connections were blocked. Captures at 1440/390 px passed
page-error, hidden-unsupported-link and overflow assertions and were visually reviewed.
They are UI demonstration material, not real Gmail/inference/production evidence.

### Finite remaining actions and approval boundary

**NO-GO for hosted V1 completion.** No new feature work is needed to describe these gates:

1. Security first: obtain approval to remove the single labelled temporary /32 rule;
   have the authorized operator remove it and verify the read-back. Coordinate
   approval, maintenance and client activation for rotation of the exposed existing
   role. Verify the old password is rejected and the updated clients work; do not
   silently trigger the current migration-on-start command during that cutover.
2. The operator restores the already verified encrypted archive into a distinct
   isolated database using protected local keys, then records schema/count/FK/unique/
   checkpoint and credential-decryption results. No passphrase needs to enter chat.
3. Source/export identity is resolved in the V03/V10 follow-up. No existing model
   has V1 quality approval. Freeze the explicitly selected artifact and an untouched,
   representative human-reviewed holdout before one final evaluation under the
   unchanged policy. Do not recycle the consumed development sample. Any classifier
   improvement/retraining or V1 scope change requires a separate explicit decision.
4. Resolve the database's expiry/zero-cost continuity constraint with an authorized
   decision; no paid upgrade or hosting migration has been inferred or performed.
5. Obtain target-host evidence for configuration/runtime DB privileges, TLS/proxy/
   cookies/private logging and bounded sync with concurrent Inbox under actual memory
   limits. Empty metrics or CI success cannot substitute for that acceptance.
6. Only after those prerequisites pass, approve the exact owner-only migration to
   e6fb80357cd1 and pinned deployment, with a verified backup and rollback compatible
   with pending failure metadata. Then execute V17 live acceptance before tagging V1.

The GitHub branch and portfolio materials can be reviewed now, explicitly as a release
candidate. They are not a declaration that every V1 gate is closed. No main merge,
production deploy, live migration, credential/network change or mailbox deletion
was performed in this closure pass.


## V03 / V10 focused closure evidence — 24 October 2026

This follow-up changes evidence/documentation only, based on release HEAD `1d37c4647f45bef5762b432be08f6a12f856f23f`; application candidate remains `b3225fa`. It supersedes the earlier checkpoint-mismatch interpretation, not the unrelated release gates. Full details and safe aggregate evidence: [V03/V10 report](docs/release/V03_V10_EVIDENCE.md), [JSON](docs/release/v03-v10-20261024.json).

**V03 technical provenance PASS; release-model approval remains BLOCKED by V10.** The existing FP32 export's source is `results/checkpoint-3159/model.safetensors`, SHA-256 `97a26b679690d2ab8df85f4e5b8fab2b7c91c8011807ac04767c4a9790a1e3d4`. The prior `1686c767…` comparison was with separate `email_classifier` weights. Tokenizer hashes match exactly; parsed configs differ only by omitted `use_cache: false`. Fresh Torch/ONNX comparison passes on 111 inputs at the unchanged 0.0001 score tolerance, with 111/111 top-one agreement. The checkpoint's original training report/split is unavailable: do not claim complete training reproducibility or silently promote it. The existing alternative v2 has a training report but poorer reviewed-development performance; no existing candidate has V1 approval.

**V10 FAIL, rating C.** Fresh evaluation reproduces the baseline's 32/100 correct (32%), top-one macro-F1 0.2839, 14 Finance false positives and 18 wrong high-score predictions. Separate heuristic slices: English **20/56 (35.71%)**; Arabic-heavy **1/11 (9.09%)**; mixed **10/32 (31.25%)**; other **1/1**. The original script's stricter script-presence categories contain only **one Arabic-only example (0/1)**; neither language convention establishes representative Arabic quality. The 100 examples are already-consumed, deliberately difficult human-reviewed development, with zero Business, four Finance and two Travel examples. They are not a final holdout or general accuracy claim.

The existing release gate status was rerun against the correct source hash: **representative human-reviewed final holdout evaluation is missing**. All original thresholds remain unchanged (>=300 examples, >=20/class, >=50 Arabic and English, accuracy >=90%, top-one macro-F1 >=85%, plus all per-class/Finance/calibration/language-gap/ambiguity limits). No final labels were opened. Tests: **29 passed, 2 skipped, 2 subtests passed**; initial seven Windows temp-directory setup errors resolved with a fresh workspace-local basetemp. Skips are explicit opt-in browser and saved-reference artifact tests; the separate fresh 111-input parity run passed. See the report for exact commands/results.

**Exact remaining action:** explicitly freeze a selected artifact, supply a separate untouched representative human-reviewed holdout with the existing group-disjoint manifest and sampling policy, then run the existing one-time final evaluation under the unchanged gate. Do not recycle development examples. Poor development results remain a warning, not a forecast or a reason to lower thresholds. If baseline acceptance is not pursued or the final gate fails, a bounded classifier-improvement or release-scope decision requires separate authorization; no retraining/model search is started here. V03's approval requirement and V10 are not declared closed. No deployment, Gmail, database, credentials, hosting or UI changes were made.


## Final portfolio/source scope closure — 25 October 2026

**PORTFOLIO SOURCE RELEASE: COMPLETE**

**HOSTED PRODUCTION RELEASE: NO-GO**

The user explicitly authorized closing the portfolio/source scope while keeping failed production gates open. V03 technical provenance is verified (111/111 parity); classifier approval is blocked and V10 remains FAILED. Original training split/report is unavailable. No thresholds, training data, artifacts or application code were changed. The final default-branch experience now leads with experimental classification, accurate setup prerequisites, synthetic screenshot provenance, architecture, test evidence and production limitations.

The operator's final instruction confirms temporary external PostgreSQL IP-rule removal and verification; that item is resolved by operator evidence, not a new inspection here. The previously exposed role password remains an unresolved security risk because coordinated rotation is deferred. Encrypted backup checksum/decryption/archive-list evidence remains valid; isolated restoration is still unverified. Live Render remains the operator-reported f53e22c with auto-deploy off; no deployment or infrastructure change was performed.

[Final freeze ledger](docs/release/PORTFOLIO_FREEZE.md) records all V01–V18 dispositions, the publication boundary, prior versus current verification, and only genuine remaining production blockers. Final GitHub HEAD and CI results are confirmed after the normal non-force push and reported in the final handoff; the commit's GitHub Checks remain the authoritative publication result. No merge, history rewrite or new development phase is authorized by this closure.


## Public interactive demo acceptance — 25 October 2026

**PUBLIC PORTFOLIO DEMO: GO.** The isolated frontend-only deployment is shareable at
https://inbox-nizer-demo.onrender.com/ with no Google account or login. All 24 messages,
example categories/summaries and ten source-linked tasks are authored fictional data.
Existing inbox/detail/tasks/navigation components are reused; no AI inference, Gmail
synchronization, backend API or database participates. The example notice and disabled
connection action prevent a false claim of live Gmail or approved classification.

Deployed commit `0d383fea7bd913f63ffe752c22919859d88c39d3`; static site
`srv-dbeuol4s728c73dh4n5g`; deployment `dep-dbeuolks728c73dh4o8g`. Both associated
GitHub CI runs passed. Local verification: clean locked dependency install, 11 demo
regressions and 173 total frontend tests, typecheck/lint, normal private build and
static-demo build. Actual public HTTPS and deployed build identity were verified;
Edge passed 1440/390px, Arabic/English, filters/pagination, details/tasks, keyboard
skip-link and fresh-route/reload tests with zero external/API requests, credential
reads, cookies or runtime errors. See [the launch report](docs/release/PUBLIC_DEMO.md)
and [aggregate acceptance results](docs/release/public-demo-verification.json).

No paid compute, live migration, model change, OAuth/secret change, data deletion or
network-rule change was introduced. The demo is independent of the expiring database.
Auto-deploy is disabled. README and the repository Homepage now point to the verified
website. Full Gmail-connected production remains NO-GO for the previously recorded
quality/security/restore/capacity/continuity gates; these do not block the isolated demo.
