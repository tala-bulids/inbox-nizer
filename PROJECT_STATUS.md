# Inbox-nizer — project status and V1 release contract

Last audited: **23–24 October 2026**. Code baseline: **`05f452ab0c168c376153f0ddae84b044c73bfb53`**, branch **`codex/inbox-nizer-release`**.

This is the single source of truth for current product scope, release blockers and remaining work. Historical reports describe their dated experiments, not current release approval. Update this file when a checklist item is verified; include the tested commit, environment and evidence. Do not mark work complete merely because code exists.

**Current verdict:** suitable for a supervised demonstration in a prepared environment; **not yet a reproducible, independently usable portfolio V1 or a verified hosted release**. The user reported a real Gmail run reaching 1,585 messages. That is useful integration evidence, not proof that this latest commit, classifier, all visible features or recovery paths are live on Render.

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

The current release commit includes **`[skip render]`**. Code was pushed, but its new migration and model artifact were not deployed in the preceding work. Do not push an unmarked follow-up commit to an auto-deploying service before those prerequisites are ready. Live deployed SHA, service configuration, database provider/revision, and current plan limits are **unverified** in this audit.

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

`frontend/src/app/App.tsx` mounts authenticated providers around Inbox `/`, Detail `/email/:id`, Search `/search`, Ask `/ask`, Tasks `/tasks`, and Settings `/settings`. `/oauth/complete` is a public callback-result page which navigates successful consent back to the authenticated app. `Shell.tsx` currently exposes all feature links unconditionally.

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
| Gmail consent, refresh/reconnect | Implemented/tested; user-reported live | Live revoked-token flow and user-facing disconnect still need completion |
| Bounded/resumable sync, History and deduplication | Implemented/tested; user reports 1,585 imported messages | Latest automatic-sync commit is not verified deployed; poison-message and exhausted-retry UX need work |
| Automatic open/focus/periodic sync | Implemented/tested | Requires an active browser; actual cold starts and multiple-tab behavior need host checks |
| Inbox, detail, filters, priorities, summaries, tasks | Implemented/tested | Chronological order, quality review and a few status/copy fixes |
| ONNX classifier on Render profile | Integration and local parity tested | Approved artifact identity/hosting, Linux memory and live classifications unverified |
| Semantic Search | Implemented/tested in full runtime | No embeddings means empty results; old embeddings can trigger heavy runtime loads on Render |
| Ask | Extensive implemented/tested full-runtime paths | Only some mailbox-plan paths avoid embeddings; general extraction depends on retrieval; generation has further runtime requirements |
| Disconnect / deletion | Backend disconnect and operator `delete-user` exist | No Settings disconnect control; no clear user data-retention/deletion instructions |
| Health, CI, operational docs | Implemented locally | Remote CI result, actual host controls, restore drill and release recipe unverified |
| Training and evaluation | Offline training/evaluation path and mechanics tests work | No approved representative quality result established by this audit |

## 5. Problems and work classification

### MUST SHIP — V1 blockers

| ID | Confirmed issue or unknown | Evidence / bounded remedy |
| --- | --- | --- |
| B1 | Release source, public repository entry and deployment are not one reproducible unit | Competing worktrees; build/start/runtime requirements exist only as uncommitted experiments; remote default `main` does not show the release. Selectively reconcile, record actual hosted SHA/config, publish one recipe and point reviewers to the verified release branch. |
| B2 | Hosted feature surface exceeds the protected runtime | Only `email_pipeline.py` and `predict.py` read `INBOX_RUNTIME_PROFILE`. `Shell.tsx`, `routes.py`, `rag_api.py`, `embedding_service.py` and `local_llm.py` do not gate unsupported features. Hide hosted Search/Ask and guard direct requests before any model work. |
| B3 | Classification is not yet a qualified hosted feature | New FP32 artifact not provisioned; Linux memory/latency and approved source identity unknown. Readiness intentionally checks no model. Add a release-time artifact/inference check, not heavy inference to health probes. |
| B4 | Inbox “newest” is import chronology | `routes.get_saved_emails` and `readInboxState` default to `created_at`; older mail imported later can lead the inbox. Use a documented message-date order with stable tie-breaks and missing-date behavior. |
| B5 | Enrichment exhaustion has no effective normal-user retry | Failed stages leave retry selection after three attempts. Update now need not revisit an unchanged failed email. Detail shows only a generic unavailable notice; Settings can report Mail updated. Provide a bounded targeted retry/recovery path and truthful partial status. |
| B6 | A permanently bad source can prevent progress beyond its page | Failed IDs rotate but remain in `state.pending`; new listing waits for that queue to empty. Cursor safety is good, but repeated failures can stop the whole account after the client retry cap. Add explicit recoverable attention state and a durable failure policy; never advance a cursor by silently losing an ID. |
| B7 | Users cannot stop the connection from the UI | `DELETE /gmail/accounts/{id}/connection` exists; Settings/API client does not expose it. Wire that existing operation, prevent further sync, explain retained data and the existing operator deletion procedure. Do not confuse local disconnect with revoking Google consent. |
| B8 | Deployment security/recovery is unproven | Actual runtime role, owner connection, direct/session pooling, TLS/proxy, limits, logging and backup restoration need evidence. Do not assume nginx examples apply to Render. |
| B9 | Core AI value lacks a bounded representative acceptance review | Existing quality tooling and historical reports are not new approval. Freeze the existing artifact, assess classifications and task/summary usefulness, report supported language/sample limits, and decide once. No automatic retraining project. |
| B10 | Documentation and acceptance evidence contradict the current product | README/frontend README still describe explicitly starting sync; OPERATIONS mentions Continue sync and older schema. Correct current instructions and publish exact verified scope, setup, screenshots and results. |

Security detail for B8: release readiness checks `pg_has_role(..., 'USAGE')` for some owner privileges. That does not test every role a connection could assume. Review effective privilege escalation/`SET ROLE` and privileged membership on the actual PostgreSQL version. The original workspace's stronger candidate checks are worth reviewing, but their mock tests do not prove live grants. PostgreSQL distinguishes these predicates in its [official role-privilege documentation](https://www.postgresql.org/docs/current/functions-info.html).

### SHOULD FIX — bounded polish/reliability, not reasons for another architecture

| ID | Work | Why / stopping point |
| --- | --- | --- |
| S1 | Align status and onboarding copy | Inbox empty state still directs users to manually sync; Settings promises later retries even after the retry cap; connected/no-new-mail and initial-empty states need distinct truthful wording. Required retry-state corrections are part of B5/B6; remaining copy is polish. |
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

All boxes below are open release work, not permission to begin implementation during this audit. Each item has a bounded verification result. Complete MUST items; do not expand the release to absorb every SHOULD/LATER item.

| Order | Priority / item | Depends on | Done when |
| --- | --- | --- | --- |
| V01 | MUST — disposition the remaining alternate-worktree deployment/security changes | This audit | A short include/archive decision exists for the deployment scripts, experimental ONNX/RAG guards and stronger role checks; release source remains on the requested branch, without a bulk merge. |
| V02 | MUST — inventory the existing hosted setup | V01 | Record service/frontend URLs, deployed SHA/branch, build/start/proxy, runtime profile, DB provider/revision/connection mode and free-plan selection; record secret **names only**. |
| V03 | MUST — identify the approved existing classifier | V01 | Source checkpoint, tokenizer/config/weight hashes and intended languages are recorded; the ONNX export matches that source and no model is silently promoted. |
| V04 | MUST — commit one reproducible Render build/start recipe | V02, V03 | Fresh build installs required dependencies and hash-verified artifact; startup performs no training/download/migration; proxy/callback and one-worker settings are reproducible. |
| V05 | MUST — gate unsupported hosted Search/Ask paths | V02 | Hosted navigation and direct API requests agree; Render tests prove no Torch/SentenceTransformer/Qwen load through disabled paths; full/local behavior remains tested. |
| V06 | MUST — fix inbox chronological ordering | None | Three messages imported out of date order render by the documented Gmail/message date, including ties/missing dates and pagination. |
| V07 | MUST — make failed enrichment recoverable and status truthful | V03 | A classifier failing three times remains visible as incomplete; a bounded retry after repair actually produces saved classification; successful Gmail sync is not presented as completed enrichment. |
| V08 | MUST — resolve persistent source-failure recovery | None | A malformed message across multiple pages has an explicit durable outcome/recovery path; good messages can progress without silently dropping the failure or advancing History unsafely; retries remain bounded. |
| V09 | MUST — expose existing disconnect and retention behavior | None | Disconnect from Settings prevents further sync, preserves/deletes data only as documented, and leaves a working reconnect path; operator deletion instructions are tested in disposable data. |
| V10 | MUST — run one finite core-quality review | V03 | Freeze one artifact and review a fixed, recorded sample with existing tools. Set acceptance thresholds before scoring, report category/language coverage and task/summary errors; either approve the limited beta or record a specific failed gate. No invented accuracy claim. |
| V11 | MUST — verify deployment security controls | V02, V04 | Runtime/owner roles and assumable privileges are verified; auth/CSRF/isolation, TLS/cookies, safe logging and request/admission limits work on the actual proxy topology. Document disconnect/deletion and invited access. |
| V12 | MUST — qualify Linux resource and timing limits | V04, V05 | Cold/warm classification, long messages, a five-message sync and concurrent inbox read stay within the actual RAM/admission budget with headroom, no OOM and no ordinary batch exceeding the client's 90-second deadline. Record measurements; Windows RSS is not acceptance. |
| V13 | MUST — pass the final automated candidate checks | V05–V09 | Targeted regressions then backend/frontend suites, API drift, lint, build and relevant browser smoke pass at one candidate SHA; every skipped check is either executed separately or justified by excluded scope. Remote CI is checked. |
| V14 | MUST — prove backup restoration before migrating real mail | V02 | A protected backup restores into a separate database; aggregate counts, constraints, schema and credential decryption are checked without exposing data; rollback path is recorded. |
| V15 | MUST — apply the additive migration safely | V13, V14 | Migration owner applies through `e6fb80357cd1`; existing accounts, emails and progress remain intact; restricted runtime readiness passes. No destructive downgrade or mailbox rebuild. |
| V16 | MUST — deploy one pinned candidate | V11–V15 | Actual hosted SHA equals the tested candidate, artifact is verified, correct origin works, health succeeds and a real new email receives a saved category. |
| V17 | MUST — complete live journey/recovery acceptance | V16 | Connect/returning account, multi-page import, usable inbox during sync, refresh/reopen, new-mail History update, no-change update, timestamp, duplicates, token reconnect, disconnect and two-tab cases have recorded results. Use approved test accounts/content only. |
| V18 | MUST — publish the bounded portfolio release | V10, V17 | README/docs match shipped scope and commands; sanitized screenshots/short demo and limitations are available; a clean clone can follow setup; reviewer links open the verified release branch rather than old default `main`; tag the verified commit and update this file with all evidence. Any merge/default-branch change requires separate authorization. |

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

- Add regressions for B2, B4–B7 before fixing them; retain current full-runtime, tenant/CSRF and advisory-lock tests.
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

V05 implemented locally: backend-owned runtime profile hides Search/Ask navigation and blocks direct frontend routes; backend rejects both APIs with `runtime_disabled` before retrieval/model work. Full/local paths remain intact. Regression-first backend run: 4 expected failures. After fix: hosted capability + Render sync tests **22 passed**; frontend capability + full Search/Ask tests **37 passed**. Frontend required execution outside the Windows sandbox because esbuild could not traverse parent directories. No deployment performed. V06–V09 remain open until individually verified below.

V06 implemented: default `message_date` sorts by `COALESCE(sent_at, message_at)`, unknown dates last in either direction and ID ties matching direction. Filtering precedes pagination; explicit `created_at`/priority/ID options remain compatible. Backend date regressions failed before the fix; inbox suite **32 passed** after it. Frontend inbox/detail suite **18 passed** (an existing navigation assertion was corrected to await the detail page rather than matching the outgoing inbox). OpenAPI and generated types updated.

V07 implemented: `POST /emails/{id}/retry-enrichment` attempts one stored email, shares the account advisory lock, preserves source data, skips completed/runtime-disabled stages and does not reset automatic attempt counters. Automatic processing now respects an exhausted stage even if another stage is pending. Detail exposes an explicit retry; Settings reports failed enrichment separately from Gmail update success. Regression-first test failed on missing recovery state. Final targeted backend **34 passed, 1 skipped** (opt-in batch latency); frontend detail/Settings **50 passed**. Repaired classification persistence, exhausted retries, no automatic retry loop, and cross-owner denial verified. OpenAPI/types regenerated.
