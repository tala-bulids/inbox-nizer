# Documentation index

Start with the [project README](../README.md), [live demo](https://inbox-nizer-beta.onrender.com) or [current showcase setup](SHOWCASE_GUIDE.md).

## Current entry points

| Document | Purpose |
| --- | --- |
| [Showcase guide](SHOWCASE_GUIDE.md) | Runtime, private artifact prerequisites and local startup |
| [Project status](../PROJECT_STATUS.md) | Deployed application reference followed by a dated development timeline |
| [Latest screenshots and acceptance](showcase-portfolio/README.md) | Actual final frontend captures and saved live checks |
| [Final memory evidence](free-qualification/MEMORY_OPTIMIZATION.md#final-measured-verdict--pass) | Completed Linux qualification and precise measurement scope |

## Research evidence

These are dated experiments, not instructions to repeat the work or claims of independent test performance.

- [Phase 2: classification](phase2/README.md), [model card](phase2/MODEL_CARD.md), [dataset card](phase2/evidence/dataset-card.json), [comparison](phase2/evidence/experiment-comparison.json).
- [Phase 3: retrieval, answers and task extraction](phase3/README.md), [original FP32 benchmark](phase3/benchmark-v1.json).
- [Free-runtime comparison](free-qualification/comparison.json) and [completed memory qualification](free-qualification/MEMORY_OPTIMIZATION.md).
- [Historical DistilBERT provenance and quality gates](release/V03_V10_EVIDENCE.md). The earlier checkpoint's results are not an eligible ranking against the newly trained classifiers.

## Historical implementation and delivery records

The following retain what was true at each phase. Statements such as “not deployed,” “NO-GO,” or “approval required” describe that dated record; consult the current status above for the deployed showcase.

- [Earlier model setup](MODELS.md), [earlier validation ledger](VALIDATION.md), [October source freeze](release/PORTFOLIO_FREEZE.md).
- [Phase 4 UI work](phase4/README.md), [Phase 5 release candidate](phase5/README.md), [initial Free qualification](free-qualification/README.md).
- [Original deployment design](../deploy/README.md), [showcase transition proposal](../deploy/AI_SHOWCASE_RELEASE.md), [final transition preparation](../deploy/AI_SHOWCASE_FINAL_TRANSITION.md).
- [Frontend implementation notes](../frontend/README.md), [final polish preparation](../frontend/FINAL_POLISH.md).
- [October Gmail screenshots](portfolio/README.md) and [earlier implementation reports](history/).
- [README before this portfolio update](https://github.com/tala-bulids/inbox-nizer/blob/3ea9d607cebffe9e3e8cbbc80097caa6e9518600/README.md), retained in commit history.

The historical `main` and `codex/inbox-nizer-release` branches remain available. Current showcase code is on `codex/ai-showcase-phase1`. Private mail, credentials, training data and fitted model artifacts are not included in this documentation update.
