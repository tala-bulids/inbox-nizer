# Free-serving qualification — 1 November 2026

**NO-GO for deployment. Prepared candidate, not Render acceptance. Free only.**
This supersedes Phase 5's compute recommendation; it does not erase its evidence.
Starting HEAD: `50461b520c3c253189bcbaedcd5fb7dd9c328884`, branch
`codex/ai-showcase-phase1`. Original Torch E5, classifier artifacts, Gmail code,
database and the public service remain unchanged.

## Explicit candidate and quality

`SHOWCASE_RUNTIME=e5-int8-fp32-corpus-v1` selects `showcase.free_app:application`.
Queries use the existing INT8 multilingual E5 ONNX graph and compact SentencePiece
tokenizer. The 80 source chunks from 24 authored CC0 fictional emails use their
original normalized FP32 E5 vectors, prepared offline. This avoids loading Torch
or re-embedding the immutable corpus at startup. This is learned semantic retrieval,
followed by the existing deterministic, source-grounded extractive answering and
task extraction. It is not LLM generation. No Qwen, paid API, database or OAuth.
Live classification remains the hash-verified Phase 2 research candidate A.
The original factory/default Engine path is retained.

The fixed corpus is a justified bounded optimization, not a search over models or
question-specific answers. Its vectors were extracted from the previously measured
Torch receipt after checking that receipt's SHA against Phase 5 evidence. The
committed index records the receipt hash, source revision, chunk IDs and collection
version; runtime verifies its own SHA, dimensions and normalization. It fails
closed if the corpus changes. `showcase.prepare_corpus` provides offline recomputation
with the pinned original E5; an additional local recomputation attempt was stopped
under resource contention and is **not claimed as completed verification**.

Real repeated results on the existing 20-question development suite:

| Metric | Original Torch | All INT8 probe | Candidate (INT8 queries / FP32 corpus) |
|---|---:|---:|---:|
| Recall@5 | 0.761905 | 0.761905 | 0.797619 |
| Recall@3 | 0.750000 | 0.738095 | 0.678571 |
| MRR | 0.761905 | 0.720238 | 0.827381 |
| nDCG@5 | 0.698971 | 0.686680 | 0.736454 |

Candidate English/Arabic Recall@5: **0.833333 / 0.761905**; Recall@3:
**0.785714 / 0.571429**; MRR: **0.761905 / 0.892857**. Token IDs match
the original for all 20 probes. Citation sets/statuses are unchanged; citation
precision 0.96875, exact evidence sets 18/20, status 20/20, missing-evidence
abstention 6/6. Tasks: 12 true positives, zero false positives/negatives on the
existing fixtures, all labelled deadlines/source references correct; only four
negative English examples, no Arabic negatives. q09/q10 failures remain.

These are consumed, same-author development probes, **not independent quality
acceptance**. Recall@3 regresses, especially Arabic. On 1 November 2026 the owner
explicitly accepted this measured trade-off **for the labelled research showcase
only**. This is not deployment approval, production quality acceptance or a waiver
of Linux capacity testing. Production thresholds were not lowered.
Historical 32/100 remains a failed difficult-development check, not accuracy.
Classifier A's English validation accuracy 0.883721 / macro-F1 0.704303 is unchanged;
Arabic and final-test classification remain unevaluated. No retraining occurred.
Model Lab distinguishes the serving candidate from historical saved metrics.

## Real combined measurement and limits

[comparison.json](comparison.json) contains safe aggregates and receipt hashes.
Raw receipts remain ignored locally; no private model or fitted vocabulary is published.
`results/free-candidate-v1.json` exercised the actual factory with real ORT + sklearn:

- Windows fresh process, warm models before listening: 5.187 s startup.
- Peak process working set **397.879 MiB**, final RSS 373.824 MiB.
- First HTTP Ask 74.465 ms and classifier 55.403 ms, **after startup warmup**.
- Warm Ask p50/p95 27.791/63.147 ms; classifier 25.471/26.489 ms (five samples each).
- Maximum 512-token encoder 1151.727 ms; 6000-character classifier p95 421.742 ms.
- Four concurrent Ask requests: one 200, three bounded 429 responses.
- Arabic and long queries exercised; oversized question 422, oversized body 413;
  historical analysis endpoint 404, readiness identifies the candidate.
- No Torch/Transformers/SentenceTransformer, database or Gmail imports observed.

This is **not** container peak memory, a 0.1-CPU measurement or a disk-cache-cold
startup. Headroom below 400 MiB process memory is negligible; Linux/container
overhead is unknown. Docker/Podman and a WSL Linux distro are unavailable here.
No Linux resource run was performed. `showcase.resource_verdict` correctly returns
FAIL for this receipt. Minimal Linux dependency CI is not a capacity substitute.
The initial diagnostic run failed before readiness because the probe selected a
redirect route instead of the API mount; the harness was corrected and rerun.

## Secure artifact acquisition

Exact sizes and SHA-256 values are in [free-manifest.json](../../showcase/free-manifest.json),
consistent with the previous model identities. Local acquisition verified all three:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| model_int8.onnx | 118065353 | b35fd7c9f9fbbd1f046393ea005fee4f1ce43e62ad905f720d1fa79c376273d7 |
| sentencepiece.bpe.model | 5069051 | cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865 |
| candidate.joblib | 2552375 | ad110b70dae9b9875e37ca43103519e23ff4afcb79219ded99ca02d38c8ce11d |

An operator-provided **private descriptor file** must map exactly those filenames
to either an approved local `path` or direct HTTPS `url`. A signed URL may be used
only when its operator has approved the host/access. No actual host or credentials
have been selected. Redirects, HTTP, URL userinfo, unexpected names, oversize data,
wrong hashes and overwriting different existing files are rejected. Downloads use
temporary files and atomic exclusive installation only after validation. CLI errors
do not echo the descriptor/URLs. Joblib is verified before deserialization.

```sh
python -m showcase.acquire_artifacts --descriptor /private/approved-descriptor.json --output local_models/showcase-free
```

Local files are not automatically available to Render. The remaining delivery
action is to provide approved, authenticated direct HTTPS access to these exact
artifacts and a private descriptor available during build. Do not put weights,
vocabulary or signed URLs in Git or model bytes in environment variables. Render
secret files have a combined 1 MB limit, so cannot carry the model files. A small
descriptor could use a secret-file binding only after approval; saving such a file
can trigger a deploy. No binding was created. See the
[Render documentation](https://render.com/docs/configure-environment-variables).

## Reproduction and Linux qualification (not yet run)

Build using `sh deploy/build-showcase-free.sh` with the approved descriptor path.
For local inference set the nonsecret variables in the transition runbook. Then:

```sh
python -m showcase.release_probe --encoder free-candidate --output results/new-free.json
python -m showcase.resource_verdict results/new-free.json
cd frontend
SHOWCASE_URL=http://127.0.0.1:4181 SHOWCASE_EXPECT_RUNTIME=e5-int8-fp32-corpus-v1 SHOWCASE_EVIDENCE_DIR=../results/free-browser node scripts/check-phase4.mjs
```

The browser script needs Playwright and Microsoft Edge, and a separately running factory
on port 4181. It tests both widths, languages, actual questions, tasks, citations,
classification, metrics and refresh. Diagnostic probe routes bind loopback only
and must never be used as the public start command.

On an already approved Linux Docker host, the prepared runner performs the test
without adding a hosting service. The actual constrained run remains **NOT EXECUTED**:

```sh
python -m showcase.qualify_linux --models /approved/local/bundle --check
python -m showcase.qualify_linux --models /approved/local/bundle --output /approved/local/new-evidence-directory
```

Use an existing private model directory and a new evidence directory. Start from
a clean committed checkout. The runner verifies the three exact hashes before
using Docker, builds `git archive HEAD` through a binary stream (no ignored/private
files in the build context), and records the source SHA and local image ID.
It mounts only the three model files read-only, never the surrounding directory.
No model files are uploaded to CI, a registry or a public repository.

Docker constraints are `--memory=512m --memory-swap=512m --cpus=0.1`
(536,870,912 bytes, no swap, 10% of one CPU), with 128 PIDs maximum. Runtime has
no network, no inherited host environment, no published port. Container peak includes
the probe client as well as the service. Require completed real inference, finite
cgroup v2 limits, explicit zero OOM counters, and <=400 MiB peak. The 60-second startup deadline may
fail at 0.1 CPU; report failure rather than silently expanding it. A successful
local container run still requires real Render/browser acceptance after approval.

`qualification.json` retains external exit/OOM evidence if the entire container
dies before writing `linux-free.json`. The child probe now records a final
observer cgroup snapshot even after startup failure; incomplete OOM counters,
invalid limits and all-rejected concurrency cannot yield a pass. A 600-second
overall deadline stops a stalled run. Only this invocation's stopped container is
removed; local models, logs, receipts and image are retained. Cleanup failures are
recorded for manual inspection. Raw receipts remain private/local until sanitized.
`--check` verifies prerequisites only and must never be reported as real inference.

The 1 November follow-up rechecked available tools: no Docker/Podman executable or
WSL distro. The exact local bundle passes hash verification, then runner preflight
returns **BLOCKED** before any container/build. Linux peak memory, cold start,
throttled latency and concurrency remain unavailable. A names-only request for an
authorized Linux host/model path or an approved local Linux setup is pending.

## Outstanding release boundaries

1. Real constrained Linux CPU/container-memory evidence.
2. Approved private build-time artifact locations/descriptor.
3. Names-only live environment/group/secret-file inventory. The owner confirms
   Dashboard access is unavailable; keep this pending and do not guess names or
   secrets. No values were read or printed.
4. Exact transition approval and subsequent target-host/public browser acceptance.

The research-ranking decision is closed by the owner's limited acceptance above.
Independent production-quality gates remain open.

No deployment, service mutation, database access, migration, deletion, credential
rotation, billable resource, public artifact upload or Homepage change occurred.
See [the transition runbook](../../deploy/AI_SHOWCASE_RELEASE.md) for the proposed
operation and data preservation boundaries. Final test/CI evidence is recorded
in `verification.json` and PROJECT_STATUS.md; no unavailable measurement is a pass.

## Initial published verification (before the measurement follow-up)

Implementation: `94f209df4c1d8086771367cf8b419a107c789d3c`. Test-only CI namespace
correction and final tested SHA: **`181f2117526b9bcd9cfc7140f8d041c2050aee1c`**.
[CI 41278976790](https://github.com/tala-bulids/inbox-nizer/actions/runs/41278976790)
passed all three jobs: 1,467 backend tests, 6 skips, 2 passing subtests; 186 frontend;
74 isolated showcase/1 private-artifact skip; 13 ML pipeline; 26 minimal Linux
runtime tests; quality unittest 11 run/1 opt-in skip. Pip checks, API contract,
typecheck, lint and standard/demo/showcase builds passed.

Local showcase: 75 passed, including real private classifier; 17 runtime tests
also passed after normalizing the pinned public index to Git's LF bytes. ML: 13;
focused frontend: 13. Initial local full frontend was interrupted after timing
failures under resource contention; the full clean CI run passed. The first CI
run incorrectly rejected Protobuf's shared `google` namespace; the corrected
check rejects actual Gmail/OAuth clients. No runtime dependency was added for it.

[Real browser evidence](browser-verification.json) confirms both widths/languages,
original/new questions, missing-evidence handling, tasks/citations, selected A
inference and hash, saved Model Lab metrics, deep links/refresh, no private API or
third-party browser requests, cookies or browser storage. The candidate identity
was checked in the portfolio response and visible notice. Reviewed safe captures:
[desktop Model Lab](screenshots/1440-lab-en.png),
[mobile Arabic evaluation](screenshots/390-evaluation-ar.png).

The final documentation/evidence-only follow-up skips redundant CI. It preserves
the application/test content of the green SHA. No deployment occurred and all
remaining boundaries above remain open; CI does not qualify Render capacity.

## Measurement follow-up verification — 1 November 2026

Base `410c563`; published tested preparation SHA
`dff8e4323ac7696537ec18cbcb30af3a5b65948b`.
[CI 41283334140](https://github.com/tala-bulids/inbox-nizer/actions/runs/41283334140)
passed: 1,486 backend / 6 skips / 2 subtests; 186 frontend; 93 isolated showcase /
1 private-artifact skip; 45 minimal-runtime checks; 13 ML pipeline; quality unittest
11 run / 1 opt-in skip. Pip checks, API contract, typecheck, lint and all three
builds passed. Local affected showcase suite: 94 passed, including actual private
classifier inference. Final evidence follow-up is documentation-only.

No new Linux inference metrics were produced. The runner preflight verified the
local model bundle then blocked on missing Docker; it started no container.
The owner-approved research ranking trade-off remains accepted. Private build-time
artifact delivery and names-only Render inventory remain pending. No serving
model, UI, production configuration, data, credential or billing change occurred.
