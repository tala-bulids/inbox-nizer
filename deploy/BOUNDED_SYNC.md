# Bounded Gmail sync operations

The new migration is `d5ea7f246bc0`, after `c4d9e6f135ab`. It adds `gmail_sync_states` and nullable `emails.sync_generation`. It was tested only in the isolated test database. **Production migration and sync were not run.**

Deploy with traffic/sync stopped, a verified backup and the separate migration-owner connection. The runtime role requires SELECT/INSERT/UPDATE/DELETE on `gmail_sync_states`, plus its existing email/stage permissions; it must not receive DDL/ownership privileges. Do not deploy this sync implementation before the migration/grants. Readiness compares against the new Alembic head. Existing source columns and rows are unchanged by the migration.

Each authenticated sync POST processes at most five pending message IDs and two Gmail listing pages (`maxResults=50`), then at most five full-scan reconciliation deletions and one older enrichment retry. Counts refer to that batch. `has_more=true` means more work remains; Settings exposes Continue sync and reads persisted account progress after reload. An operator/API client may invoke the same endpoint again serially. Do not run overlapping requests or an unbounded tight retry loop. There is no installed background scheduler.

The 20-second budget is soft: checks happen between operations, including after listing a page, not by interrupting an atomic provider request. Provider transport timeouts remain 30 seconds; application retries happen in later batches. In the full runtime, one local model call may exceed the budget. The Render Free profile below excludes those calls. Target-host wall time, CPU/RAM and mixed-workload capacity remain unverified.

## Render Free runtime

Set `INBOX_RUNTIME_PROFILE=render-free` on the Render backend and redeploy the
release branch. No schema migration or OAuth configuration change is needed for
this profile. The default, including an absent environment variable, is `full`.

Render Free sync runs `clean`, the existing model-free extractive `summary`,
`tasks`, and `facts`. It never calls the classifier, embedding preparation, or
SentenceTransformer during sync. `classify` and `embedding` receive terminal
`skipped` states with `runtime_disabled` as the reason, without incrementing
attempts or deleting original mail or existing derived data. These markers are
saved before deadline checks, so interrupted heavy stages also become terminal
when that email is retried. Older interrupted emails are still handled at the
existing bounded rate of one enrichment retry per batch; they are not bulk-reprocessed.
Only genuine pending/failed work keeps `has_more` true. New category predictions
and semantic vectors are unavailable for emails synced under this profile.

Switching back to `full` restores all stages when an email is next processed;
skipped states are not treated as completed inference. No automatic backfill,
threads, workers, or scheduler is added. This profile limits Gmail sync only;
other explicit AI endpoints are outside its memory guarantee.

An overlapping sync can still correctly return 409. Wait for the active bounded
request before retrying. Redeployment stops any old process still running model
inference; do not delete checkpoints or attempt to unlock another live session.
Use a direct PostgreSQL connection (or session pooling), not transaction pooling,
because the account lock must remain on the same PostgreSQL session across commits.
Acquisition errors and unsuccessful/interrupted unlocks invalidate the pinned
connection so a possibly locked session is never returned to the pool.

## Durability and recovery

The full-sync anchor is captured before listing. Page tokens, current-page pending IDs and the final candidate history ID are committed before body retrieval. Each original source and its pending enrichment marker commit before optional enrichment. Stage results are independently committed; model computation for classification, summary and embeddings holds no database transaction. The published History cursor changes only after every source ID and full-scan reconciliation are acknowledged. Source uniqueness and stage hashes make replay idempotent. Derived-stage failure can remain retryable after the source cursor advances.

A pinned connection holds a PostgreSQL session advisory lock per account across the short transactions. `finally` releases it; failed unlock invalidates the connection instead of pooling a lock. Process/connection loss releases the lock at PostgreSQL. Reconnect/disconnect use the same lock. Restart resumes the durable state; no token/cursor is accepted from the browser. OwnedSession scopes checkpoint reads/writes as well as messages. Monitor pool availability: each active sync reserves one connection.

HTTP 404 on History schedules full recovery without advancing the committed cursor. Expired page tokens restart from the committed History anchor or a fresh full-scan generation. Other provider failures retain pending work. A repeatedly failing source blocks cursor advancement and is reported; retry/reconnect after resolving the cause rather than silently skipping it. Prior failed/interrupted enrichment gets one retry per batch even without new Gmail history.

Full reconciliation still follows the existing Gmail mirror semantics: only after a complete scan, remove locally mirrored messages absent from Gmail in bounded groups. A message GET 404 follows existing deletion semantics. No such reconciliation, deletion or sync was executed against production by this task. A newly connected mailbox's first full scan must be explicitly started by its owner.

Rollback: stop the service/sync, retain the DB backup and old artifacts. Prefer application rollback with additive schema retained. The schema downgrade refuses while a continuation row exists; do not delete checkpoints merely to bypass the guard. Decide explicitly whether to finish or abandon a job, preserving original mail and the last committed History cursor. Rehearse on a restored disposable database first.

Protocol references: [Gmail History pagination and expired-cursor behavior](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list), [Gmail synchronization guide](https://developers.google.com/workspace/gmail/api/guides/sync). These describe provider behavior, not evidence of a live-provider deployment test.
