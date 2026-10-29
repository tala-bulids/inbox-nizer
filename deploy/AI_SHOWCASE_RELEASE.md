# Existing-service AI showcase transition — approval required

29 October 2026. **Prepared, not applied. PUBLIC AI SHOWCASE: NO-GO.**
Do not execute a deploy, save Dashboard settings that automatically deploy, change
compute, attach a disk, alter credentials, or run a migration from this document
without the owner's explicit approval of the exact transition.

## Verified current state

Workspace `tea-d5domjogjchc73dquke0` (Tala's); service
`srv-dbcqvja9lscs73er2pu0`, `inbox-nizer-beta`, Frankfurt, Python, Free, one instance.
Existing public URL: https://inbox-nizer-beta.onrender.com.
Branch `codex/inbox-nizer-release`; auto-deploy **off**. Latest reported live deploy
`dep-dbdg1abncjis73a2vvg0`, source `f53e22cd3c4a881671e06ab6a00b3bd2b9d393c0`.
This is the old Gmail application, not the showcase. Current start command:

```sh
python -m alembic upgrade head && python -m uvicorn render_wrapper:app --host 0.0.0.0 --port $PORT --proxy-headers
```

The current build generates `render_wrapper.py` importing `main`, installs the full
root requirements and builds the ordinary frontend. No health-check path is set.
The older static demo is untouched and does not watch the development branch.
No other service in the inspected workspace watches `codex/ai-showcase-phase1`.
A normal push to this branch therefore does not trigger the inspected services.

Memory/CPU/latency metric queries returned empty series. The error-log query
returned no entries. These are **unavailable evidence**, not zero usage or success.
Environment values, secret-file contents and private Postgres were not inspected.
A live browser request is deferred: waking the existing Free process can run the
old startup migration before any webpage is served.

## Compute decision (not a purchase request)

The unchanged real Torch/E5 + selected A + API stack peaked at **918.21 MiB** on
Windows; FP32 ONNX peaked at **940.32 MiB**. Neither qualifies for 512 MB Free.
The existing INT8 export peaked at **398 MiB**, but ranking regressed: MRR
0.76190 -> 0.72024, nDCG@5 0.69897 -> 0.68668. Recall@5 and citation sets were
unchanged. That export is an **offline probe**, not the selected runtime. It needs
an explicit documented trade-off decision, supported serving integration and
Linux/Render qualification before any Free claim. No threshold was lowered.

[Render compute plans](https://render.com/docs/compute-plans) list Free 0.1 CPU/
512 MB and `1c-2g` at 1 CPU/2 GB. The smallest listed RAM tier above the unchanged
measured process is therefore **1c-2g**, listed at **US$25/month** in
[Render's official pricing example](https://render.com/articles/production-rails-hosting-guide).
The $7 plan still has 512 MB and does not resolve this memory requirement. Prices
exclude any applicable workspace, bandwidth or tax charges. This is a candidate
resource tier, not proof of Linux fit or capacity. No paid plan is activated.
The owner has not authorized hosting spend. Do not treat this document as approval.

## Artifact boundary

The classifier is private local `results/phase2-A/candidate.joblib` (2,552,375 bytes),
SHA-256 `ad110b70dae9b9875e37ca43103519e23ff4afcb79219ded99ca02d38c8ce11d`.
Its fitted vocabulary must not be uploaded to this public repository. No approved
private build-time delivery channel is available in this task. The operator must
approve/provide one for this exact artifact; do not invent an artifact host or
embed the model in an environment variable. Treat the joblib file as executable
input; only the recorded hash can be deserialized. The UI's research warnings and
failed historical production-quality gate remain visible.

The publicly licensed pretrained E5 model is revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`; provision its snapshot before runtime,
verify all hashes in `docs/phase2/evidence/encoder-artifact-manifest.json`, and
retain its MIT attribution. No source dataset rows or private mail are needed.
The release factory checks identity and warms models offline. Missing artifacts
cause a sanitized startup failure, never fallback predictions.

## Exact proposed configuration after the boundaries are resolved

Keep **the same service and URL**, one Python 3.11 process, auto-deploy off, no
persistent disk, no DB, no Google login, no workers. Use the final reviewed SHA on
`codex/ai-showcase-phase1`; never deploy an unreviewed moving branch tip.
The selected unchanged runtime requires separate approval for `1c-2g` paid compute.
If the owner selects Free instead, stop: the INT8 path is not integrated/approved.

1. Privately record rollback metadata and the names of existing service variables,
   linked environment groups and secret files. Do not print/export their values
   into chat or Git. Current secret names/group/file inventory is **unverified**.
   Preserve the existing database/accounts/credentials and any operator-held
   rollback material. The prior encrypted backup/untested restore evidence is
   unchanged and is not needed to read the showcase's fictional corpus.
2. Present and approve the exact set of service variable/group/file bindings to
   detach. Detach all mailbox DB/OAuth/token/encryption material from this web
   service, preserving the underlying resources and shared groups for other uses.
   Do not rotate credentials or delete anything. The startup name guard is extra
   protection, not a substitute for inspecting file mounts/groups.
3. Replace the old build/start commands **before any deployment**. Remove any
   pre-deploy command and automatic migration. Do not import `main` or the old
   generated wrapper. Point HTTP health checks to `/api/health/ready`.
4. Provision the approved private classifier during build. Until that operation
   is specified and approved, the build below is intentionally not turnkey.
5. Deploy the approved SHA manually once, inspect its sanitized logs and metrics,
   and run real public acceptance. Plan changes and Dashboard saves can trigger
   deployments: use a reviewed atomic configuration operation or keep the service
   paused during the approved maintenance window; never trigger the old command.

Runtime environment allowlist (platform-injected variables are separate):

```text
PYTHON_VERSION=3.11.9
HF_HOME=/opt/render/project/src/.cache/huggingface
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
TOKENIZERS_PARALLELISM=false
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
EMBEDDING_DEVICE=cpu
SHOWCASE_CLASSIFIER_PATH=/opt/render/project/src/results/phase2-A/candidate.joblib
```

Build proposal, **not executed on Render**; private classifier delivery must occur
before it completes. Fresh Linux package installation is not yet qualified:

```sh
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r deploy/requirements-showcase.txt
python -m pip check
HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 python -c "from huggingface_hub import snapshot_download; snapshot_download('intfloat/multilingual-e5-small', revision='614241f622f53c4eeff9890bdc4f31cfecc418b3')"
npm --prefix frontend ci
npm --prefix frontend run build:showcase
```

Start proposal (no Alembic, no historical app; one worker avoids duplicate models):

```sh
python -m uvicorn showcase.release_app:application --factory --host 0.0.0.0 --port "$PORT" --workers 1 --no-access-log --timeout-keep-alive 5
```

This factory performs real startup inference, verifies the two model identities
and does not expose its ready endpoint until initialization completes. It blocks
historical classification while preserving offline/local implementations. Do not
serve `showcase.release_probe`; its diagnostic endpoints are loopback-only tools.

## Public acceptance and rollback

After the approved switch, use a fresh anonymous browser on the original HTTPS
URL. Run `frontend/scripts/check-phase4.mjs` with `SHOWCASE_URL` set to that URL and
`SHOWCASE_EVIDENCE_DIR` set to a new ignored evidence directory. Cover both widths,
RTL/LTR, unseen questions, abstention, evidence links, tasks, new classification,
model metrics, refresh and no private APIs/browser storage. Test cold readiness,
429/413/422, sanitized missing-artifact errors and maximum allowed inputs. Inspect
real deployment source SHA, logs, request-body logging configuration, peak memory,
OOM/restarts and latency. Missing metrics do not count as a pass. No public
traffic or logs should contain private mailbox records or Google credentials.

If acceptance fails, stop advertising the new deployment. Do not blindly roll
back to a start command that runs Alembic. Any restoration of the private Gmail
service/configuration is a separate approved action after checking its startup
and schema compatibility. Do not undo data or rotate credentials as rollback.

Only after public acceptance: update the main README live announcement and GitHub
Homepage to the verified original URL, record exact deployed SHA/model hashes and
retain honest validation/Arabic/independent-holdout limitations. The CV text and
architecture are already prepared in `docs/phase5/README.md`.
