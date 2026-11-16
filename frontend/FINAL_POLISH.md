# Final frontend and content polish

**Follow-up, 16 November 2026:** this frontend was deployed as [3ea9d60](https://github.com/tala-bulids/inbox-nizer/commit/3ea9d607cebffe9e3e8cbbc80097caa6e9518600) on 15 November, with Arabic/English desktop/mobile acceptance completed on 16 November. [Actual captures and evidence](../docs/showcase-portfolio/README.md).

## Original preparation record

Prepared on 15 November 2026 for approval. No deployment performed.

The public showcase now opens with a short bilingual introduction at `/`.
Ask Mail is at `/ask`; existing task, collection, lab and legacy intelligence
routes remain available. The palette and monospaced wordmark are retained, with
readable body typography, fewer borders, clear navigation, and responsive RTL/LTR.

## Content and evidence

| Claim                               | Existing evidence used                                                                                    | Boundary kept in the UI                                                                                                                  |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Classification data and splits      | `docs/phase2/evidence/dataset-card.json`                                                                  | 2,103 usable English examples; 1,679 train, 215 validation, 209 reserved test; test not evaluated                                        |
| A/C classifier results and training | `docs/phase2/evidence/experiment-comparison.json`, `training-configuration.json`, `docs/phase2/README.md` | Validation used for selection; no independent final test or Arabic classifier evaluation                                                 |
| Historical DistilBERT fine-tuning   | `docs/release/V03_V10_EVIDENCE.md`                                                                        | Earlier v2 experiment trained last two layers for three epochs; distinct from the later evaluated checkpoint with missing original split |
| Historical failed gate              | `docs/release/v03-v10-20261024.json`                                                                      | 32/100 on difficult consumed development examples; English 20/56 and Arabic-heavy 1/11 are small heuristic slices, not general accuracy  |
| Retrieval and tasks                 | `docs/phase3/benchmark-v1.json`                                                                           | Original FP32 Recall@5 76.2%; task F1 1.00 on 16 authored fixtures; two answer-evidence mismatches; not independent human evaluation     |
| Deployed architecture               | `showcase/free_runtime.py`, `showcase/engine.py`, `showcase/intelligence.py`, `showcase/portfolio.py`     | INT8 E5 query encoder + precomputed FP32 corpus, selected sparse classifier, deterministic task rules, extractive answers                |
| Final memory optimization           | Existing private workflow run 41783099933, source `73ebaf5a5693f2064628b9be935e3267af2fa702`              | Exact constrained Linux cgroup peak, not sampled Render memory                                                                           |
| Existing deployment success         | Completed acceptance for `dep-dbskjtdg1s2s73ff8et0` at `c2ef87094bc01860b6e763f02dafe799d88dca13`         | Hosting acceptance only; frontend polish still awaits deployment approval                                                                |

The existing sanitized memory receipt was read, not regenerated. SHA-256:
`5467dcc30939c76f1f43845249d27fef2b79069af2227eb168eeec1c9adc3c46`.
Baseline/final container peak: 524296192 / 349323264 bytes
(500.0078125 / 333.140625 MiB), reduction 33.372916%.
Maximum encoder input remained 512 tokens; latency changed from
3.896259 to 6.599054 seconds under 0.1 CPU, 512 MiB and no swap.
The final allocation change left weights, input bounds and quality aggregates unchanged.
The earlier INT8 adaptation is described separately from that final memory change.

Visible frontend strings were rewritten in Arabic and English. Original fictional
message text and computed model output remain intact. Meaningful dates inside
messages are preserved; reference-calendar metadata and ordinary-visitor version
IDs are removed. No task priority is invented: the backend does not return it.

## Focused verification

- `npm run build:showcase`: PASS (existing third-party Zod annotation warnings only).
- `npm test -- src/test/showcase.test.tsx`: **14 passed**.
- ESLint on changed showcase, test and browser script files: PASS.
- Prettier on changed TSX, TS, CSS and browser script files: PASS.
- `node scripts/check-final-polish.mjs`: PASS using the unchanged real offline
  runtime on loopback at port 4182, existing models and installed ONNX dependencies.
- Arabic/English at 1440 and 390 px: real original/novel questions, abstention,
  citations, task source/deadline handling, editable classification with matching
  artifact hash, saved metrics, confusion tables, reproduction document,
  navigation and deep-link refresh.
- No page errors, page-level horizontal overflow, third-party browser requests,
  private API calls, cookies or browser storage.
- Saved aggregate results: [final-polish-verification.json](final-polish-verification.json).
  The 32 full-page screenshots are generated locally in
  `results/final-frontend-polish/screenshots/` and are provided in the approval handoff.

The initial browser attempts exposed a textarea label issue and a shared header
style conflict; both were corrected. The harness also now waits for navigation
before changing a source. A metadata assertion was narrowed to preserve actual
UTC times in the original email text. The final full run passed after these fixes.

## Acceptance review

- **Visitor:** the homepage explains the idea and offers direct trial/lab links;
  answers and supporting messages are separate, and tasks use familiar labels.
- **AI engineer:** the lab distinguishes fitted features/heads, pretrained
  encoders, historical fine-tuning, validation, research fixtures, deployed
  inference and constrained memory measurements. Detailed metrics remain accessible.
- **Recruiter:** a concise project introduction leads to working features and a
  clear technical narrative, with a subtle repository link and no commercial claims.

Only frontend source, focused tests, browser acceptance and this content evidence
are included. Backend/model files, deployment settings, credentials and data are
unchanged. No training, memory qualification, infrastructure or paid service was run.
The pre-existing unstaged memory document update is excluded from this commit.
