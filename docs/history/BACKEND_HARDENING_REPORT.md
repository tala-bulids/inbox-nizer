> Historical local development report, preserved from the accessible workspace. Its results are not new verification or a claim of production readiness. See ../../README.md for current setup and ../VALIDATION.md for this update.

# Production backend hardening — implementation report

**Decision: B.** The multi-user backend is implemented and covered by 870 passing
tests. Live activation is still pending explicit legacy mailbox ownership,
encrypted-token configuration and Google reconnection. The existing local DB role
is a superuser; deployment must replace it with a limited runtime role. Test success
is not evidence that those operational steps have happened.

## Architecture and behavior

1. **Before:** one unowned inbox, shared plaintext `token.json`, unscoped database
   sessions/search/RAG, cookie-only OAuth state, one-page full fetching, raw Date
   strings, and enrichment inside the route before source persistence.

2. **Risks found:** cross-user ID/search/fact exposure; shared credentials; lost
   source messages on optional processing failures; no incremental cursor,
   pagination or sync lock; unconditional insecure OAuth transport setting; and
   potentially sensitive query strings in server access logs.

3. **Ownership:** `AppUser -> GmailAccount -> Email -> all email children`.
   Children inherit ownership through their email FK instead of duplicated user IDs.

4. **Application authentication:** operator-issued 256-bit opaque bearer tokens,
   stored as SHA-256 hashes with expiry and revocation. IDs supplied by a client
   cannot authenticate that client. Default lifetime is seven days, maximum thirty.
   Browser login/SSO is separate future frontend/deployment work.

5. **Gmail accounts:** multiple accounts per application user; normalized mailbox
   address is unique across accounts. Google's profile identifies the mailbox.
   Another user's OAuth callback cannot overwrite or take over that account.

6. **Credential persistence:** account-FK `oauth_credentials` table. OAuth attempts
   have hashed one-use state, owner, browser-nonce hash, encrypted PKCE verifier
   and ten-minute expiry. Access/refresh tokens never appear in response schemas.

7. **Encryption:** authenticated Fernet/MultiFernet from `cryptography`, `v1:` format
   prefix, environment key ring and operator rotation command. Missing/invalid
   keys or malformed ciphertext fail safely. First offline consent requires a
   refresh token; reconnect retains the existing refresh token if Google omits it.

8. **Legacy token file:** runtime neither reads nor writes `token.json`. It was
   neither exposed nor deleted. Reconnect using the new flow; retire/revoke the old
   file manually after verifying the new connection.

9. **Sync:** full paginated bootstrap followed by Gmail history-based incremental
   sync. Added/changed messages are fetched; authoritative message-GET 404 deletes
   the local message and children. Successful full recovery reconciles absence.
   All Google calls remain read-only.

10. **Cursor:** bootstrap captures the profile history ID before listing to avoid
    missing changes during pagination. Incremental sync reads every history page.
    The final cursor advances only when all required source writes succeeded.

11. **Expired cursor:** history-list 404 triggers full recovery. Other provider
    errors preserve the cursor and return safe failures; they do not silently skip
    events. Retryable API calls use three retries and bounded request timeouts.

12. **Idempotency:** database uniqueness on `(account_id, message_id)`, deduplicated
    history IDs/messages, and hashed/versioned processing stages. Replaying a page,
    retrying a failed sync or restarting after rollback does not duplicate emails.

13. **Concurrency:** PostgreSQL transaction advisory lock per account rejects
    overlapping sync with 409. Account row locks serialize reconnect/disconnect.
    Bootstrap is synchronous and holds a transaction; large-mailbox load testing
    remains necessary before scaling.

14. **Pipeline:** source payload/headers/timestamps are stored first. Cleaning,
    classification/priority, summary, tasks/deadlines, facts and embeddings run
    through one reusable pipeline, with savepoints for independent stages.

15. **Failure/retry:** stage status, attempts, hash, version and safe error code
    persist. Source messages survive optional failures. Later sync retries failed
    stages even without new Gmail events. Changed-content failures cannot become
    successful merely by adopting old derived results on retry. Detail responses
    expose safe processing state. Logs contain IDs/stages/error types, not bodies
    or exception strings. A crash before commit rolls the sync back for replay.

16. **Timestamps:** `sent_at` and Gmail `message_at` use timestamptz; input is
    normalized to UTC. Raw header `email_date` remains for compatibility/provenance.
    `created_at`, sync time and event/deadline dates retain distinct meanings.
    PostgreSQL may display equivalent aware values in the session timezone.

17. **Legacy dates/ownership:** migration parses safe RFC Date headers and records
    `parsed`, `missing`, `invalid` or `naive` status without guessing a timezone.
    Gmail internal timestamp stays NULL until fetched. Existing rows go to a
    disabled `legacy-quarantine` account, not an inferred real identity.

18. **Schema:** six new tables: `app_users`, `app_access_tokens`, `gmail_accounts`,
    `oauth_credentials`, `oauth_attempts`, `email_processing_states`. Email gains
    ownership, typed timestamps, parse status, raw payload and Gmail labels. No
    historical migrations or AI fact/vector schema definitions were rewritten.

19. **Migration:** `alembic/versions/b3c8d5e024fa_backend_ownership.py`, following
    `a2b7c4d913ef`. Upgrade preserves IDs and children. Downgrade refuses once an
    account leaves quarantine, avoiding silent loss of established ownership.

20. **Constraints/indexes:** account/message uniqueness; unique mailbox address;
    owner/account/email cascading FKs; indexes on account owner, token owner,
    OAuth-attempt owner, processing email and `(account_id, created_at, id)`.
    Existing child indexes and HNSW remain. No claim of large-scale performance
    is made; tests verify SQL scope precedes vector ORDER BY/LIMIT.

21. **API boundary:** fresh, immutable-principal `OwnedSession` from authenticated
    `get_db`; central loader criteria for all owned mappings; guarded writes and
    rejection of Core/raw/bulk request operations and unsafe mixed projections.
    Unknown mappings are denied until explicitly covered. Unknown and foreign
    email/account IDs return the same 404. Filters/pagination/sorting remain.

22. **Semantic search:** ownership is in the SQL candidate query before ranking
    and limiting, not a Python post-filter. Tests inspect SQL and candidates.

23. **RAG:** retrieval, metadata/context reconstruction, reranking and citation
    source sets use the same scoped session. Tests inject another user's source,
    use two independently authenticated HTTP clients and reject foreign citations.
    Prompts, models, embeddings and reasoning heuristics were not tuned.

24. **Facts:** both fact and checkpoint queries inherit ownership through Email;
    current provenance/hash checks remain. Another user's facts cannot populate
    the current user's deterministic answer.

25. **Security review:** fixed the shared credential authority, missing ownership,
    insecure-transport override and state binding. Added encrypted PKCE storage,
    replay rejection, secure production cookie behavior, redirect validation,
    generic public errors, query-log redaction and no-store responses. No wildcard
    CORS/debug endpoints were added. `.env`, `credentials.json` and `token.json`
    are not tracked. This was not a complete historical Git secret scan or an
    external penetration test. Privileged operator SQL is explicitly outside the
    request-session boundary; it must never be exposed through a data route.

## Files and verification

26. **Exact files changed in this phase:**

    New:

    - `account_routes.py`
    - `authentication.py`
    - `backend_admin.py`
    - `backend_config.py`
    - `backend_models.py`
    - `email_pipeline.py`
    - `gmail_sync.py`
    - `ownership.py`
    - `privacy_middleware.py`
    - `alembic/versions/b3c8d5e024fa_backend_ownership.py`
    - `test_backend_isolation.py`
    - `test_backend_migration.py`
    - `test_backend_sync.py`
    - `BACKEND_HARDENING_REPORT.md`

    Modified:

    - `README.md`
    - `conftest.py`
    - `database.py`
    - `email_serialization.py`
    - `gmail_auth.py`
    - `gmail_service.py`
    - `main.py`
    - `models.py`
    - `requirements.txt`
    - `routes.py`
    - `semantic_search.py` (defer raw payload in list results)
    - `test_deadline_storage.py`
    - `test_email_facts.py`
    - `test_email_facts_migration.py`
    - `test_email_processing.py`
    - `test_gmail.py`
    - `test_inbox_api.py`
    - `test_oauth.py`
    - `test_semantic_migration.py`
    - `test_semantic_search.py`
    - `test_summary_storage.py`
    - `test_task_storage.py`

    Previous dirty AI/training files and dump files were preserved. In particular,
    existing changes in `rag_service.py`, `rag_retrieval.py`, `fact_store.py`,
    `email_facts.py` and the relational-fact modules were not edits from this phase.
    No staging, commit or push occurred.

27. **Tests:** 78 additional parameterized cases net over the 792-test baseline.
    Coverage includes two-user API/SQL/vector/fact/RAG isolation; bearer expiry and
    revocation; account/message uniqueness; encryption/rotation/wrong keys;
    refresh persistence/revocation/missing refresh token; state/PKCE/expiry/replay/
    takeover; full/history pagination, duplicate events, 404 recovery, deletions,
    transient/partial failures, retry and overlapping locks; each enrichment failure;
    stale-result retry; dates; cascades/disconnect; legacy ownership and migration.
    Existing Gmail mocks were adapted to POST and the new service boundary. Old
    failure tests now assert that optional failure preserves the original message.

28. **Full pytest:** **870 passed, 1 warning in 12.78s**. Latest complete run used
    `.\env\Scripts\python.exe -m pytest -q --maxfail=2`; no failure occurred, so
    the entire suite ran. The warning is the existing Starlette/httpx deprecation.
    All Python executions used the project's `env` interpreter. No GGUF model,
    live Gmail calls or paid APIs were used by tests.

29. **Migrations:** the historical chain and new upgrade/downgrade/re-upgrade pass
    against an isolated schema in the `_test` database. Tests preserve parent IDs,
    raw dates/body, tasks, vectors, facts and fact checkpoint content; verify invalid
    dates and verify the downgrade guard. Transaction rollback removes the schema.

30. **`git diff --check`:** only the pre-existing unrelated trailing whitespace in
    `test_main.py:37` remains. No new whitespace finding from this phase.

31. **Real local database modified?** No. Only read-only verification was run
    against `ai_smart_inbox`; its Alembic head remains `a2b7c4d913ef`.

32. **Backup created?** No new database backup: there was no local migration or
    reprocessing. Existing dump files were untouched. README provides the backup
    step before manual activation. A workspace source snapshot was used to
    distinguish this phase's edits from pre-existing changes.

33. **Emails preserved?** Read-only counts before/after confirm **89 emails**.

34. **Facts preserved?** Read-only counts before/after confirm **42 facts**.

35. **Other persisted AI data:** **129 embedding chunks, 89 fact checkpoints**.
    Test DB cleanup was also checked: zero emails, chunks, facts, fact checkpoints,
    credentials and non-quarantine accounts remained after tests.

36. **Manual live Gmail incremental sync?** Not performed. The real mailbox owner
    has not been explicitly bound to an application identity and encryption keys
    are not provisioned. A real Uvicorn process was started and stopped safely:
    health returned 200; inbox/accounts/semantic search returned 401 without a
    token; responses had `Cache-Control: no-store`. Authenticated multi-user flows
    ran through ASGI/HTTP tests against PostgreSQL with fake Gmail/LLM providers.

## Required operator steps and conclusion

37. **Manual setup:** see README's **Production backend architecture → Configuration
    and manual activation**. Confirm who owns the legacy mailbox first. Back up;
    apply `b3c8d5e024fa`; provision encryption keys; create the application user;
    authorize Swagger with its bearer token; connect Gmail using
    `POST /auth/google/start`; verify the returned account address/ID; explicitly
    run `backend_admin.py claim-legacy --account-id <verified-account-id>
    --confirm-ownership` **before first sync**. Then run the account sync twice to
    validate live bootstrap/history behavior. No identity or account ID is guessed.

38. **Environment:** added `OAUTH_TOKEN_KEYS`, `GOOGLE_CLIENT_FILE`,
    `GOOGLE_REDIRECT_URI`, `APP_ENV`. Existing database/test/model settings remain.
    No real environment/credential/token file was edited. Public routes require
    bearer authentication; sync intentionally changed from GET to POST. `/ask`
    request/response contract remains unchanged.

39. **Remaining production gaps:** live reconnection/history validation; explicit
    legacy ownership; limited runtime DB role (current local role is superuser);
    TLS/proxy log hygiene, secret custody/backup restore drills, resource/rate limits,
    monitoring and retention controls. CLI-issued bearer tokens are usable for
    controlled backend clients, but browser login/SSO/recovery/MFA remain frontend/
    deployment work. Large sync transactions need scale testing. ORM policy relies
    on trusted server code; it is not PostgreSQL RLS or protection from a compromised
    privileged operator. Google token rotation plus DB persistence cannot be one
    atomic cross-system transaction; a DB failure after rotation may require reconnect.

40. **Decision B:** substantial, tested architectural improvement with explicit
    operational safety gaps remaining. The implementation is reviewable and ready
    for controlled local activation after ownership confirmation. It is **not** a
    claim of completed production rollout or live Google validation.

Implementation references: [Gmail sync](https://developers.google.com/workspace/gmail/api/guides/sync),
[SQLAlchemy loader criteria](https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html#sqlalchemy.orm.with_loader_criteria),
[Fernet](https://cryptography.io/en/latest/fernet/).
