# Existing Render release recipe and recovery gate

Prepared 24 October 2026. **Not deployed.** PROJECT_STATUS.md owns the release verdict.
This recipe preserves the existing native Python service, mounted `/api` and built
React SPA. The nginx/systemd examples in OPERATIONS.md describe a different,
self-managed full-runtime setup; do not apply them to this service.

## Verified inventory (read-only Render MCP)

- Workspace: Tala's workspace (`tea-d5domjogjchc73dquke0`).
- Service: `inbox-nizer-beta`, `srv-dbcqvja9lscs73er2pu0`, Python, Free,
  Frankfurt, one instance, empty root directory, previews off.
- Repository: `tala-bulids/inbox-nizer`, branch `codex/inbox-nizer-release`.
- SPA/browser origin: `https://inbox-nizer-beta.onrender.com`; API origin is the
  same, under `/api`. No separate static site was found for this application.
- Live deploy: `dep-dbdg1abncjis73a2vvg0`, commit
  `f53e22cd3c4a881671e06ab6a00b3bd2b9d393c0`, completed 23 October at 06:43:39 UTC.
- Auto-deploy is off; health-check path is empty.
- Existing build installs all of requirements.txt, builds the frontend, then
  generates render_wrapper.py. Existing startup runs `alembic upgrade head`
  before Uvicorn. Neither command was changed in the Dashboard.
- PostgreSQL: `inboxnizer-beta-db`, `dpg-dbcquaa9lscs73eqtki0-a`, PostgreSQL 18,
  Free, Frankfurt, available. No managed connection pool, replicas or HA.
  Closure recheck: one temporary /32 rule, "Temporary laptop backup", remains.
  Removal is NOT verified. The application URL/role and any external
  pooler remain unverified; session advisory locks require session affinity.
- Database expiration reported by Render: **2026-11-21 06:37:29.181483 UTC**.
  A durable zero-cost beta cannot be promised with that expiration unresolved.
  No paid upgrade or hosting migration is authorized by this recipe.
- Earlier read-only SQL through hosted MCP was refused when the allowlist was
  empty. The later temporary laptop rule does not establish MCP access. No firewall rules were changed. No schema/count/key/backup result
  can be inferred from the platform saying the database is available.
- Metrics returned empty memory/latency series. Public HTTPS probes from this
  workstation timed out (35 seconds per request); availability/TLS/cookies
  and proxy behavior are not verified by this inspection.

[Render Free limits](https://render.com/docs/free) include expiring Free Postgres,
web-service spin-down and ephemeral web storage. The classifier is a reproducible
build artifact; all mailbox/source/checkpoint/credential persistence stays in
PostgreSQL. No local web filesystem is a mailbox backup.

## Proposed configuration — apply only after release approval

Keep this service, region, plan, branch and single instance. No new service,
Blueprint, paid disk, worker, scheduler or inference API is needed.

- Build command: `bash deploy/render-build.sh`
- Start command: `bash deploy/render-start.sh`
- Health path after schema/role validation: `/api/health/ready`
- Python: tested locally with 3.11.9. Node: 24; npm uses the committed lockfile.
  Validate that exact Python version is available on Render before activation.
- Required runtime names: `APP_ENV=production`,
  `INBOX_RUNTIME_PROFILE=render-free`, `CLASSIFIER_RUNTIME=onnx`,
  `DATABASE_URL`, `OAUTH_TOKEN_KEYS`, `GOOGLE_CLIENT_FILE`,
  `BROWSER_ORIGIN`, `GOOGLE_REDIRECT_URI`, `GOOGLE_LOGIN_REDIRECT_URI`,
  `GOOGLE_LOGIN_ALLOWED_EMAILS`, `CLASSIFIER_ONNX_PATH`.
- Build artifact names: `CLASSIFIER_BUNDLE_URL`, `CLASSIFIER_BUNDLE_SHA256`.
  URL must use HTTPS; checksum must identify the reviewed four-file FP32 bundle.
  Do not use the experimental int8 classifier or embedding bundles.
- Preserve all existing keys and Google client contents. Keep both callback
  values on the same HTTPS origin with `/api/auth/google/callback` and
  `/api/auth/google/login/callback`. Do not rotate or regenerate credentials.
- Existing optional knobs: `GMAIL_INITIAL_SYNC_DAYS`,
  `GMAIL_SYNC_INTERVAL_SECONDS`. Render supplies `PORT`.
- Build/start set offline model flags and one native compute thread. Startup
  uses one worker and disables Uvicorn access logging. No migrations or
  request-time downloads are part of startup.
- `FORWARDED_ALLOW_IPS` is optional and must contain verified trusted proxy
  addresses; do not set `*` without verifying the ingress boundary. Defaults
  retain Uvicorn loopback trust. Confirm redirect/cookie behavior on Render.

These are **required names**, not an assertion that live variables have been
inspected. MCP exposes service commands, but no read-environment operation in
this session. Compare names privately in the Dashboard; never paste values.

The build uses pinned serving dependencies plus transitive constraints. It
rejects installed Torch, Transformers, SentenceTransformer or llama-cpp packages
and runs a synthetic offline ONNX smoke before building the SPA. When replacing
a full-dependency build, clear the build cache as part of the approved deployment
so stale packages cannot satisfy checks. Full/local requirements are unchanged.

## Artifact and quality gate

The current local source weights SHA-256 is
`1686c767582eab051298eb82fa048822b9c6142842f61b3a384f55e204f6902b`.
The existing FP32 export provenance records source weights SHA-256
`97a26b679690d2ab8df85f4e5b8fab2b7c91c8011807ac04767c4a9790a1e3d4`.
These differ. The historical classifier decision selected no release model.
Do not pack, publish or activate either as an approved production artifact until
its source/approval is resolved. Existing artifacts are preserved.

After approval, use the existing `deploy/export_classifier_onnx.py` only if a
matching export is needed (export is not training). Verify source/tokenizer
identity, top-label/confidence parity, then use `deploy/install_classifier.py
--pack <approved-export> --archive <new-ignored-archive>` and record its checksum.
The installer accepts exactly config.json, tokenizer.json, model.onnx and weights.bin.
Store the bundle in approved protected artifact storage; no private email data.

`python -m deploy.qualify_classifier --output results/<unique>/diagnostic.json`
runs 20 existing public bilingual examples and ten long inputs with fixed
performance limits. Set CLASSIFIER_ONNX_PATH to the frozen export. It does not
train, consume the human holdout or approve quality. Run on the target Linux
resource allocation in a fresh process; Windows RSS is intentionally unreported.
Additionally benchmark the full server with one bounded sync and concurrent
inbox reads. A classifier-only memory result is not whole-service capacity.

The existing classifier-release-v1 policy remains unchanged: >=300 reviewed
examples, >=20/class, >=50/language, accuracy >=90%, macro-F1 >=85%, plus its
per-class, Finance, calibration and ambiguity limits. Current inspected review
metadata has 100 development attestations and no final holdout in that directory.
Do not relabel examples, lower thresholds or consume a holdout repeatedly to pass.

## Protected backup and restoration gate — partial operator evidence

The operator supplied the following evidence on 24 October; these completed checks
were not repeated, and no passphrase was requested or printed:

- Encrypted local backup: `inbox-nizer-20261024-170201-bb51b442.dump.gpg` (Windows D: drive).
- Encryption reported: GPG AES256.
- SHA-256: `49b141a24d7dae46039e15888a1cd76509a948e6ad43a498f0fece8ebe27d191`.
- Operator results: CHECKSUM OK; BACKUP DECRYPTION VERIFIED; POSTGRESQL ARCHIVE
  LIST OK; 242 archive entries; 16 TABLE DATA entries.
- Verification scripts reported: verify_backup.py and check_inbox_nizer_archive.py.
  No separate verification manifest is confirmed. The backup was not opened,
  copied, uploaded or assumed accessible by this agent.
- **Full database restoration has NOT been tested.** These checks do not prove
  schema/count/constraint equivalence, credential decryption after restore, RPO/RTO
  or restored application operation. Continue with the isolated-restore gate below.

### Security actions requiring approval

The operator reports the password for `inboxnizer_beta_db_user` was exposed in a
screenshot. Treat that password as compromised. No exposed value is reproduced in
this repository. OAuth encryption keys and the backup passphrase are separate and
must be preserved; database password rotation does not justify rotating them.

Exact proposed operations, **not executed**:

1. On `inboxnizer-beta-db`, remove only the temporary /32 entry labelled
   **Temporary laptop backup**, then read back Networking/IP rules to confirm no
   external entries remain. This closes that laptop's direct DB access; it does not
   remove data or change Render's internal connection. Coordinate any remaining
   operator work before closing access. The closure recheck still found this rule.
2. In an approved maintenance window, rotate only `inboxnizer_beta_db_user`'s
   password using the database owner's authorized mechanism. Keep the new secret
   outside commands, screenshots and Git. Update every legitimate dependent client,
   including the existing service's protected DATABASE_URL, then activate it through
   a separately approved deployment operation. New connections can fail between
   password change and client activation; existing pooled connections are not proof
   that the new password works. The current start command auto-migrates, so do not
   blindly deploy/restart to apply a credential change before reviewing that risk.
3. Verify old-password authentication fails, new runtime connections/readiness work,
   and account/source/checkpoint data are preserved. Record only results, not secrets.
   No rotation or successful post-rotation check is claimed here.

Approval and authorized operator access are required before either operation. The
available MCP tools in this session cannot edit Postgres networking or rotate its
credentials. Do not substitute database deletion/recreation or a new public rule.

### Remaining restoration procedure

1. Obtain an authorized database connection without making the database public.
   The temporary laptop rule is not a general authorized access path for hosted MCP. An operator can use an
   existing approved network path or separately approve narrowly scoped temporary
   access. Do not add 0.0.0.0/0. Keep passwords in protected PostgreSQL service /
   password files, never shell arguments or reports. PostgreSQL 18 client binaries
   exist locally under `C:/Program Files/PostgreSQL/18/bin`.
2. Record `SELECT version_num FROM alembic_version`, public table/column/constraint
   metadata and aggregate counts for every mailbox/auth/source/derived/checkpoint
   table. Inspect runtime role using deployment_health.py's read-only predicates.
   Review direct connection/session-affinity mode; never use transaction pooling
   for the dedicated advisory-lock connection. Preserve every old encryption key.
3. Arrange a consistent backup snapshot and record the write boundary. Pause
   mailbox activity only with explicit approval. Use `pg_dump --format=custom
   --file=<protected-file> service=<approved-source>` with PostgreSQL 18. Store
   encrypted outside the repo/web root; restrict access and retain protected key
   generations separately. Agree retention, RPO/RTO and expiry recovery.
4. Inspect `pg_restore --list <protected-file>`. Restore into a **distinct isolated
   database** using `pg_restore --exit-on-error --single-transaction
   --dbname=service=<isolated-target> <protected-file>`. Never pass `--clean` or the
   live target. Verify target identity first; no app sync/Google calls may run.
5. Compare revision, counts from the same backup snapshot, FK/unique constraints,
   `(account_id,message_id)` uniqueness, account ownership and exact saved
   checkpoints/history cursors. Stream oauth_credentials.ciphertext through
   backend_config.decrypt using protected original keys; record only total /
   successful / failed counts, never ciphertext/plaintext. Also validate encrypted
   OAuth verifiers if present. Do not contact Google to validate restoration.
6. Rehearse the additive upgrade on the isolated restore to `e6fb80357cd1` using
   the separate schema owner. Verify import_query, counts, source/credential/
   checkpoint preservation and readiness with the non-owner runtime role.
   Run ownership and synthetic recovery smoke. Record timings, dump checksum,
   isolated target identity and reviewer. A file's existence is not a passed restore.

## Exact approval boundary and rollback

Only after artifact, quality, Linux capacity, security and restoration gates pass:
propose the exact tested commit and bundle checksum, necessary configuration
changes, backup identity and approved maintenance window to the user. Then stop.

The proposed approved sequence is: stop writes; final consistent protected backup;
verify backup; owner-only `python -m alembic upgrade e6fb80357cd1`; verify metadata /
counts; configure the existing service to use the checked-in commands; manually
deploy the exact candidate with approved bundle and no auto-migration; verify
readiness and hosted acceptance; reopen traffic. Never run `upgrade head` blindly.

Stabilize writes pending checkpoint entries as strings or `{id, attempts}` objects.
The currently live f53e22c reader is not a safe rollback target after new metadata
has been written. Prefer a forward fix. If incompatible rollback is unavoidable,
isolate traffic and restore the verified pre-activation backup into a separate
database, verify keys/counts/cursors, then explicitly approve switching code and
connection together. This loses post-snapshot writes and requires an explicit
recovery decision. Do not clear pending IDs, advance cursors, strip failure metadata,
run destructive downgrades or silently delete user data to make old code run.

Hosted acceptance must cover actual login/consent, automatic multi-page import,
concurrent inbox use, persisted classification, chronological pagination, History
updates/no-change, enrichment/source retry, reload/multiple tabs, disconnect/reconnect,
blocked Search/Ask, private logging and measured resource use. Synthetic local tests
are necessary but cannot replace these checks.
