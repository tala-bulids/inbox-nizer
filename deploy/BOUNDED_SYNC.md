# Automatic Gmail sync

The authenticated app starts/resumes Gmail sync on app open, eligible focus/visibility
changes, and while visible. The default freshness interval is five minutes
(`GMAIL_SYNC_INTERVAL_SECONDS=300`, clamped to 60â€“3600). Navigation between Inbox,
Settings and other routes does not stop the coordinator. The user button is
**Update now**. OAuth success enters the authenticated Inbox, where account state
is verified before sync; callback query parameters never authorize access.

## Initial import and recovery

New scans use `GMAIL_INITIAL_SYNC_DAYS=90` by default. A fixed `after:<epoch>` Gmail
query is saved on the checkpoint so changing config/restarting cannot change the
scope of a partially imported page. Set 0 only to explicitly request an unfiltered
mirror. Existing checkpoints retain their null query and continue unchanged.
Scoped imports never delete older local messages just because they fall outside
the window. Existing mail, tokens, ownership and uniqueness are not migrated.

After sources are acknowledged, `history_id` advances transactionally. Subsequent
updates use `history.list(startHistoryId=...)`, including additions, deletions and
label changes. HTTP 404 from History starts a recent recovery scan with a fresh
anchor. Confirmed message GET 404 removes that mirrored message; scoped recovery
preserves older records whose deletion can no longer be established from History.
Unfiltered legacy scans retain their bounded full reconciliation behavior.

`last_synced_at` means the last successful Gmail contact with committed source
progress, or a successful no-change update. It may advance during initial import;
it does not assert that optional enrichment has finished. `initial_sync_pending`
comes from the absence of a published history cursor; no second timestamp is needed.

## Bounded execution and failures

Each POST still handles at most five message IDs, two listing pages of up to 50
IDs, five legacy reconciliation deletions, and one older enrichment retry. The
20-second budget is soft; provider calls retain their 30-second transport timeout.
Sources commit before enrichment, and acknowledgements survive process loss.
A malformed/failing source stays pending while other IDs in its page can succeed;
its History cursor never advances past the unresolved source. No duplicate rows
can bypass the `(account_id, message_id)` database constraint.

The client awaits each POST. It stops on unchanged/cyclic progress, an uncertain
request, source failure, 90-second request timeout, 1000 batches or 30 minutes.
Operational caps are internal; normal progress automatically resumes later.
Failures back off (5, 10, 20, 30 minutes by default), then stop automatic attempts
after five consecutive failures for that app session. Manual Update now or reopening
can try again. Optional enrichment retries at most three times per input/version;
changed inputs reset attempts. Failed classifications do not block later sources.

Browser Web Locks coordinate tabs when available; the PostgreSQL session advisory
lock is always authoritative. Keep a direct/session-pooled database connection,
not a transaction pool. Acquisition/unlock uncertainty invalidates the connection.
Closing the browser, logout, or a Render restart cannot lose committed progress.
Hidden tabs pause after the current batch; there is no always-on worker, Pub/Sub,
paid service, or promise of execution while all browsers are closed.

## Render Free classification

`INBOX_RUNTIME_PROFILE=render-free` now classifies through the SAME `classify_email`
entry point using a lazy, single-session ONNX CPU export of the existing weights.
The classifier is not retrained or quantized. FP32 weights are external ONNX tensors to reduce load-time memory. Category mapping, preprocessing, 512-token bound
and sigmoid confidence semantics are preserved. Embeddings remain runtime-disabled
and are marked skipped. Torch/Transformers are never imported by this sync profile.
Previously skipped classifier states become eligible for bounded backfill.

Provision `model.onnx`, `weights.bin`, `tokenizer.json`, and `config.json` at
`CLASSIFIER_ONNX_PATH` (default `local_models/render/classifier`). Dependencies
include the pinned `onnxruntime` in requirements.txt. Export the approved existing
artifact outside production with `python deploy/export_classifier_onnx.py --source
<existing-classifier> --output <new-ignored-output-directory>`. Do not commit weights,
mailbox data, credentials or signed download URLs. Do not substitute an unverified
base checkpoint. Validate parity against that artifact and actual Linux memory
before enabling live classification. Missing artifacts produce retryable stage
failures, never fabricated labels or a silent Torch fallback.

A local ten-text English/Arabic parity probe preserved top labels and confidence
within 0.0001 of the original outputs. Backend plus classifier inference peaked at
333.9 MiB on Windows (307.4 MiB resident), without Torch or Transformers imports.
This is a functional smoke test, not an accuracy claim or Linux/live qualification.

## Deploy order and live verification

1. Hold deployment until the database/artifact prerequisites are ready. This release
   commit uses `[skip render]` to keep pushing it from triggering an automatic
   deployment. After prerequisites are verified, deploy it manually; do not push
   another unmarked commit beforehand.
2. With the migration-owner connection, apply Alembic `e6fb80357cd1` (after
   `d5ea7f246bc0`). It adds only nullable `gmail_sync_states.import_query`.
   Old rows remain null; downgrade refuses while scoped imports exist. Do not
   grant DDL to the runtime role or run migrations with its credentials.
3. Provision and verify the existing classifier export in the build artifact.
   Set the Render profile, classifier path, initial window and interval above.
   Preserve OAuth configuration, encrypted token keys and the existing database.
   Package only the four inference files with `python deploy/install_classifier.py
   --pack <export-dir> --archive <ignored-zip>`. Provision that artifact at an approved
   HTTPS location, set `CLASSIFIER_BUNDLE_URL` and its printed SHA-256 server-side,
   and append `python deploy/install_classifier.py` to the existing backend build
   command after dependency installation. Never put the URL/credentials in Git or VITE.
4. Deploy `codex/inbox-nizer-release` to the existing `inbox-nizer-beta` service.
   Verify health, actual deployed SHA and peak memory; no paid resources are needed.
5. Test a connected account: automatic recent import, progressive inbox/categories,
   navigation during import, close/reopen resume, one newly received email via
   History, fast no-change Update now, correct last update, no duplicate rows,
   revoked-consent reconnect and concurrent tabs. Do not send test mail without
   the user's chosen recipient/content and authorization.

Current local checks do not prove the production migration, artifact provisioning,
Google consent flow or live classification. Record those separately after execution.

References: [Gmail synchronization](https://developers.google.com/workspace/gmail/api/guides/sync),
[Gmail message-list query](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list).
