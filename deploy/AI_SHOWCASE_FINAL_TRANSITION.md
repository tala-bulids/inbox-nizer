# Final Free Render transition — preparation only

This note supersedes the outdated qualification, inventory and descriptor-only statements in `deploy/AI_SHOWCASE_RELEASE.md`. It does not authorize deployment.

- Qualified inference source: `73ebaf5a5693f2064628b9be935e3267af2fa702`.
- Operator-reported 4 November private Linux qualification: 333.140625 MiB peak; zero OOM; real inference. Hosted acceptance is still pending. No production quality claim.
- Existing service: `inbox-nizer-beta`, Free, one instance, auto-deploy off. Preserve the original URL.
- Owner-confirmed variables: APP_ENV, BROWSER_ORIGIN, DATABASE_URL, GOOGLE_CLIENT_FILE, GOOGLE_LOGIN_ALLOWED_EMAILS, GOOGLE_LOGIN_REDIRECT_URI, GOOGLE_REDIRECT_URI, INBOX_RUNTIME_PROFILE, OAUTH_TOKEN_KEYS, PYTHON_VERSION, RAG_PROVIDER. Secret file: `credentials.json`. No linked environment groups.

## Artifact delivery

The owner confirms the token is already securely configured in Render as `SHOWCASE_GITHUB_TOKEN`. Keep that name and value; do not request or print it. Its required scope is the private `tala-bulids/inbox-nizer-model-artifacts` repository only, Contents read-only, with a finite expiration. Permissions/expiry have not been inspected in this task. Do not also set `SHOWCASE_ARTIFACT_DESCRIPTOR`. The fixed release is `showcase-research-v1`; the provider requires the three exact assets and verifies size and SHA-256 against the existing manifest. Direct 200 or one 302 to explicitly allowed GitHub asset hosts is supported; the bearer token is never forwarded. Unsupported redirects fail closed. The shell excludes the token from dependency installers and frontend build subprocesses, and unsets it before starting the Python web process. Render retains the service secret for future builds; rotate before expiration. No live authenticated acquisition has been verified.

## Transition for approval only

1. Use the exact published SHA from the handoff on `codex/ai-showcase-phase1`. Run only focused new downloader/launcher tests. Do not trigger unrelated qualification runs; the publication commit uses `[skip ci] [skip render]`. Preserve the existing Render configuration and actual old secret values/file privately in secure owner-controlled storage; confirm recoverability before detaching bindings. The attached patch reported a 21 November 2026 database expiry; this was not independently verified and database continuity is not resolved by this release. Do not delete or modify that DB or its data. The original Gmail app stays in Git, but is not served by this public showcase.
2. Before any save, verify a safe maintenance/suspension or atomic configuration sequence that prevents a deploy using the old automatic migration command. Do not wake, restart, or roll back the old service with that command. If the platform cannot guarantee this order, stop for approval/clarification. A service-scoped maintenance window can temporarily interrupt the site; no paid upgrade or new services.
3. Under the approved safe sequence set branch `codex/ai-showcase-phase1`, build `sh deploy/build-showcase-free.sh`, start `sh deploy/start-showcase-free.sh`, health `/api/health/ready`, no pre-deploy command, and auto-deploy off. Detach the ten old variables other than PYTHON_VERSION and `credentials.json` from the service, only after securely preserving values/file. Do not rotate or delete underlying credentials or data. No new groups.
4. Retain/set `PYTHON_VERSION=3.11.9`; set `NODE_VERSION=24`, `SHOWCASE_RUNTIME=e5-int8-fp32-corpus-v1`, `SHOWCASE_EMBEDDING_DIR=local_models/showcase-free`, `SHOWCASE_CLASSIFIER_PATH=local_models/showcase-free/candidate.joblib`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and the private `SHOWCASE_GITHUB_TOKEN`. No database, Google OAuth, or secret descriptor is needed. Render injects PORT. Do not set credential values in Git. Render env vars are service secrets available to the platform; the app process is not passed the token by the start script.
5. Deploy the reviewed exact SHA only after explicit approval. Verify hashes in sanitized build logs, readiness, actual public browser flows, no private API/DB calls or credential exposure, resource and OOM evidence, latency, RTL/LTR and mobile/deep-link refresh. Stop if a mandatory check fails. Never automatically roll back to a migration-on-start deployment. A safe old-app restoration is a separate reviewed action. Update README/Homepage only after acceptance.

Focused verification on 15 November 2026: **46 passed, no skips**, including the patch's original 13 simulated HTTP checks plus redirect/error/cache and shell execution boundaries. Command: `python -m pytest --confcutdir=showcase showcase/tests/test_github_artifacts.py -q -p no:cacheprovider --tb=short --basetemp <fresh-private-test-directory>`. The Windows sandbox initially denied hard links and the Git shell; the shared system pytest directory also denied access. The successful run used the existing environment outside the sandbox with a fresh workspace-private temporary directory. No live private credentials or model downloads, Render changes, training or new full CI/qualification run occurred. Existing model identity and inference logic are untouched. The older local `codex/render-artifact-delivery` branch is not part of this publication; its differently named token/configuration must not be used.

## Exact proposed settings

| Setting | Value |
| --- | --- |
| Original service | inbox-nizer-beta / srv-dbcqvja9lscs73er2pu0 |
| Workspace / region | Recorded Tala's workspace tea-d5domjogjchc73dquke0 / Frankfurt |
| Repository / branch | https://github.com/tala-bulids/inbox-nizer / codex/ai-showcase-phase1 |
| Source | Exact published preparation SHA from the handoff; descendant of 73ebaf5 |
| Plan / instances | Free / 1 |
| Runtime / root | Python / repository root (blank Root Directory) |
| Auto-deploy | Off |
| Build | sh deploy/build-showcase-free.sh |
| Start | sh deploy/start-showcase-free.sh |
| Pre-deploy | Empty; no automatic migrations |
| Health path | /api/health/ready |
| URL | https://inbox-nizer-beta.onrender.com |
| Linked groups / final secret files | None / none after secure archival and detachment |

Final explicit variables (Render's injected platform variables are separate):

```dotenv
PYTHON_VERSION=3.11.9
NODE_VERSION=24
SHOWCASE_RUNTIME=e5-int8-fp32-corpus-v1
SHOWCASE_EMBEDDING_DIR=local_models/showcase-free
SHOWCASE_CLASSIFIER_PATH=local_models/showcase-free/candidate.joblib
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

Preserve the existing `SHOWCASE_GITHUB_TOKEN` secret variable in addition to these.
Do not add `SHOWCASE_ARTIFACT_TOKEN` or `SHOWCASE_ARTIFACT_DESCRIPTOR`. The startup
script retains the qualified allocator launcher and exactly one Uvicorn worker.

Exact proposed removal list, only after recoverable encrypted archival:
APP_ENV, BROWSER_ORIGIN, DATABASE_URL, GOOGLE_CLIENT_FILE,
GOOGLE_LOGIN_ALLOWED_EMAILS, GOOGLE_LOGIN_REDIRECT_URI, GOOGLE_REDIRECT_URI,
INBOX_RUNTIME_PROFILE, OAUTH_TOKEN_KEYS, RAG_PROVIDER; also detach credentials.json.
These are service bindings only. Preserve the database, encrypted Gmail tokens,
the complete OAUTH_TOKEN_KEYS list/order, Google client/grants and existing backups.
Nothing in this task archived, detached, revoked, rotated or deleted them.

Use non-deploying service settings updates first and environment **Save only**.
The Render env-vars bulk API replaces the collection: never accidentally omit the
already configured SHOWCASE_GITHUB_TOKEN. Do not expose its value in a payload log.
Secret-file saves can deploy; detach credentials.json last, only after the safe
commands, branch and complete environment are saved. If a safe non-deploying
sequence cannot be established, leave the live service untouched and resolve that
before execution. Do not restart the historical migration-on-start deployment.

After approval, deploy the exact handoff SHA with a clean build cache, preserving
auto-deploy off. The new build must independently verify all three hashes in
`showcase/free-manifest.json`; failed access/hash checks stop it. Public readiness,
real flows and Render resource observations are post-deployment acceptance, not
authorization to repeat the completed private qualification.
