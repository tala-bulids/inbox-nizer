# GitHub Actions Linux qualification — 2 November 2026

The owner selected GitHub-hosted Ubuntu with Docker. Local WSL/Docker installs,
restarts, SSH and Render changes are **not authorized**. This supersedes the local
Linux environment request. The research-only ranking trade-off remains accepted.

## Executable workflow and honest gates

`.github/workflows/free-qualification.yml` runs only on relevant pushes to
`codex/ai-showcase-phase1`, on `ubuntu-24.04`, with read-only repository permission
and no persisted checkout credentials. It does not use pull-request events, access
production secrets or deploy. No default-branch change or merge is needed.

1. Build the existing Dockerfile from a binary Git archive of the exact pushed SHA.
   Ignored model files, credentials and local data are not in this build context.
2. Run a real **dependency and constraint smoke check**, with no model mounts,
   under `--memory=512m --memory-swap=512m --cpus=0.1 --pids-limit=128` and no network.
   Verify cgroup v2 memory/swap/CPU limits and native ORT/sklearn imports. This is
   **not learned inference**, and its memory/latency is not model capacity evidence.
3. If an approved private descriptor exists, acquire all three exact artifacts,
   verify size/SHA before deserialization and invoke the existing full hybrid
   `showcase.qualify_linux` runner. Its actual-factory probe covers startup, Ask,
   tasks, citations, classifier A, Model Lab data, English/Arabic, maximum inputs
   and concurrent requests. Original quality thresholds and 400 MiB target remain.
4. If the descriptor is absent, record **BLOCKED**, with real inference false.
   Missing/failed build or smoke evidence is **FAIL**, not silently BLOCKED/PASS.
5. Upload only `inbox-nizer-qualification-public.json`, an allowlisted summary.
   BLOCKED or FAIL makes the final job exit nonzero. A red qualification workflow
   due to absent provisioning is deliberate; the separate normal CI can be green.

The 512m setting is 536,870,912 bytes (512 MiB), matching the existing qualification
contract. Matching memory and swap limits disables container swap; 0.1 limits CPU
time to one tenth of a core. GitHub hardware and noisy-neighbor behavior still
differ from Render. See [Docker resource controls](https://docs.docker.com/engine/containers/resource_constraints/).
Read actual cgroup evidence; passing this test would not guarantee Render acceptance.

## Private provisioning: intentionally unavailable

No approved artifact host, signed locations or provider credentials have been
supplied. No GitHub secrets were created/read, and no model was uploaded anywhere.
The current workflow contains **no provisioning provider**; it must remain BLOCKED
for real inference until the owner approves a concrete secure delivery path.

The integration contract is a reviewed provider step that writes the regular file
`$RUNNER_TEMP/inbox-nizer-approved-artifacts.json` before evidence collection.
Its three keys must be `model_int8.onnx`, `sentencepiece.bpe.model` and
`candidate.joblib`, each mapping to a single `url` field containing an approved
direct HTTPS download location. No actual location is invented or committed.
URLs/credentials stay in that mode-0600 temporary file, not shell arguments,
workflow source or environment values. The existing downloader refuses redirects,
HTTP, URL userinfo, extra names, oversized/mismatched files and silent overwrites.
Artifact identities remain in `showcase/free-manifest.json`.

Provider access must be scoped to this repository, authorized branch and reviewed
source revision. Do not attach private delivery to fork/PR code or unreviewed
workflow changes. If the provider uses OIDC, its trust policy and extra token
permission require a concrete approved configuration; none exists here. Secrets
are not proven safe merely by masking: [GitHub's guidance](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
also warns about disclosure through command lines. Do not place a private model,
even encrypted, into this public repository as a workaround.

Models download into a fresh mode-0700 directory outside checkout. Only exact
model files are mounted read-only into the no-network test container. No model,
descriptor, fitted vocabulary, raw inference receipt or raw log is uploaded as
an Actions artifact or cached. The one public artifact contains source SHA,
status, fixed reason text, verified constraints and allowlisted numeric metrics
when actual inference completes. It expires after seven days. Runner-private
files disappear with the ephemeral runner; later investigation must use a reviewed
sanitized evidence path rather than uploading the whole temporary directory.

## Reproduction and remaining operation

The authorized push triggers this workflow; no manual dispatch/default-branch
workaround is needed. After the private provider is approved and implemented on
this branch, a reviewed relevant push executes acquisition and the same constrained
runner. No frontend/model changes or retraining are needed to unblock provisioning.

For a passing real-model run, retain the exact tested SHA, source model hashes,
complete cgroup limits/peak/OOM evidence, startup and latency distributions,
concurrency and original-suite results. No memory result from the dependency smoke,
Windows, unit mocks or unconstrained CI is a substitute.

Render remains untouched. Its proposed build/start/health/nonsecret settings are
in [the existing transition runbook](../../deploy/AI_SHOWCASE_RELEASE.md). The
names-only variable/group/secret-file inventory is still pending, and deployment
still requires separate approval of the exact existing-service changes.

## Executed evidence

Tested code/workflow SHA: **`24c953b42338a69ed4b03588058d451b21f825b2`**.
The initial workflow at `a87bfc3` found a real packaging defect: the frontend
Docker stage lacked public JSON fixtures imported during TypeScript compilation.
The tested follow-up copies only those committed public evidence files.

[Qualification run 41392546684](https://github.com/tala-bulids/inbox-nizer/actions/runs/41392546684):
image build **PASS**; actual constrained Linux native dependency smoke **PASS**.
Cgroup checks verified 536,870,912 bytes, zero swap and 0.1 CPU. Real-model stage:
**BLOCKED — approved private artifact descriptor unavailable**. The final gate
exited nonzero intentionally; the workflow's failure is not an OOM or an observed
model-capacity failure. No learned inference, cold-model timing or peak model
memory was measured. [Exact public report](github-actions-20261102.json).

The only uploaded artifact is `free-qualification-public-evidence`, ID
`13117654707`, **445-byte archive**, SHA-256
`a4cf2a91064a05bfc52b766238a2adb53fdaf02c1f6752c80811a387a9ef659a`.
It contains only the sanitized report. The local runner image was
`sha256:91c27a572885e0919576bda09a84e2c546e23ad05a3cc83d85f16ff998d52b2b`;
no image or model was pushed to a registry.

[Normal CI 41392546712](https://github.com/tala-bulids/inbox-nizer/actions/runs/41392546712)
passed: 1,495 backend / 6 skips / 2 subtests; 186 frontend; 54 minimal-runtime;
102 isolated showcase / 1 private-artifact skip; 13 ML; quality unittest 11 run /
1 opt-in skip. Pip checks, API contract, typecheck, lint and all three frontend
builds passed. Local affected showcase suite: 103 passed. The final follow-up
records documentation/public evidence only and skips redundant CI.

**Next required action:** approve a private artifact location and authentication
method, then review the provider step that creates the private descriptor without
logging its contents. Re-run this workflow with the three verified artifacts.
Adding an arbitrary secret alone cannot unblock a workflow with no provider step.
No local install, SSH, restart or Render action is needed for this CI test.
