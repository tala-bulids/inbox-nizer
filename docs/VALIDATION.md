# Inbox-nizer validation evidence

**Current source freeze:** see [the final evidence ledger](release/PORTFOLIO_FREEZE.md)
and [PROJECT_STATUS.md](../PROJECT_STATUS.md). The dated results below are historical,
not the latest suite counts or production approval.

Checked locally on 18–19 October 2026 with Python 3.11.9, Node 24.11.1 and npm 11.6.2.
Direct Python requirements are pinned to the tested installed environment; the frontend
uses its existing npm lockfile. No model performance benchmark is claimed.

## Executed checks

| Check | Observed result |
| --- | --- |
| Full backend `pytest` suite | 1,318 passed, 4 explicitly skipped |
| Complete migration chain in an empty, transaction-isolated test schema | 1 passed (added after the full run) |
| Offline classifier unit suite without PostgreSQL | 9 passed (also included in the full backend run) |
| Latest local review `unittest` suite, including its opt-in browser check | 11 passed, including Windows process exclusion and blocked browser storage |
| Frontend Vitest | 135 passed across 7 files |
| Frontend TypeScript check and ESLint | Passed |
| Frontend production build | Passed |
| Production-build browser smoke | Passed at 1440, 820 and 390 pixels in Arabic and English; no overflow/page errors; synthetic API responses only |
| OpenAPI export and TypeScript generation | Generated from the current application |
| Python dependency check | `pip check`: no broken requirements |
| Python source syntax audit | 176 files parsed at audit time; no syntax errors |
| Publication scan | No private-key, GitHub-token or Google-secret patterns found in candidate text files or 418 preserved Git history objects |

The full backend suite used the explicitly configured separate `_test` PostgreSQL
database. Production-engine connections were blocked by fixtures. A writable temporary
directory inside ignored `results/` was used because the machine's existing pytest
temporary directory is inaccessible under the sandbox identity. No mailbox database
migration, reprocessing, live Gmail sync or Google consent was performed.

The classifier roundtrip creates a tiny real DistilBERT with random weights and a
synthetic tokenizer/dataset, trains one epoch, saves it, reloads it, compares runtime
and evaluation results, exercises long-input truncation and confirms that a second
training run refuses to overwrite the artifact. It makes no claim about trained-model
accuracy, Arabic performance, calibration or real-mailbox generalization.

The four skipped full-suite tests are opt-in browser review, Ask/browser integration,
runtime latency and bounded-sync latency checks. Skips are not proof those checks pass.
The review unittest count overlaps pytest and must not be added as unique coverage.
Its browser check was separately enabled and passed after incorporating the final
local process-lock and browser-storage fixes.

## Fixed verified failures

- `/email-categories` crashed before lazy classifier initialization; it now uses the
  shared category contract and does not load a model to populate a filter.
- An API unit test depended on an unpublished checkpoint; it now mocks classification,
  while the separate roundtrip verifies actual model training and inference.
- Training, prediction and evaluation selected different default model directories
  and token limits. They now share a project-relative artifact path and inference code.
- Training selected an arbitrary cached Arrow dataset. It now requires an explicit
  local dataset and supports Arrow, JSON and JSONL.
- Fresh test databases lacked the initial tables. The fixture now applies the full
  migration chain when starting empty, with a separate real PostgreSQL regression.
- Direct scikit-learn usage lacked a declared direct requirement. Python requirements
  are pinned to the tested versions rather than open-ended upgrades.
- Review tooling used a workstation-specific Documents path; its portable default is
  now the ignored `private_review/development.csv`.

## Remaining limits

- No full-size retraining or representative accuracy evaluation was run. The available
  local legacy model was not promoted or changed. Weights/data are not distributed.
- The English DistilBERT base and raw sigmoid scores do not establish bilingual quality
  or calibrated probabilities. Human-reviewed release evaluation remains necessary.
- Hosted TLS, real Google/OAuth configuration, recovery drills and production capacity
  require operator validation. Optional GGUF generation needs a compatible local runtime.
- Historical experiment scripts require their named local artifacts and previous
  experiment outputs; see MODELS.md. Historical reports are preserved, not revalidated.
- Starlette emits a dependency deprecation warning about its httpx test adapter. The
  frontend build emits third-party Zod annotation warnings. Both completed successfully.
- Secret-pattern scans are limited checks, not proof that every possible sensitive
  value is detectable. Credentials, mailbox exports and model artifacts are excluded.

GitHub Actions is configured for clean PostgreSQL/pgvector and frontend checks. Local
results above are distinct from the remote workflow result shown on the pull request.
