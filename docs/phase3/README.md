# Phase 3 — Ask Mail and evidence-linked tasks

28 October 2026. Branch `codex/ai-showcase-phase1`, base
`5b7cf7bdf1c77b9293d2431f0a91c15f5539ed1b`. Local implementation and evaluation;
no deployment, database, credential or hosting configuration change.

## Selected architecture

The public experience uses **learned multilingual E5 retrieval followed by
deterministic extractive answer composition**. It is not labelled LLM generation.
The existing optional Qwen/GGUF code remains for explicit offline callers; the
public API rejects `mode=synthesis` before any generator loads, and the public UI
does not offer that mode. No paid API, new model family or database is introduced.

1. Load the versioned JSON collection and validate bounded size, unique IDs and
   fictional sender domains. Original bodies remain intact.
2. Split into original line/paragraph spans, with at most 320 characters per chunk.
   Long spans break at whitespace. Normalize embedding text with NFC; preserve
   source offsets separately. Subject, sender and message date accompany each chunk.
   The existing encoder also checks the real 512-token limit and fails explicitly
   rather than silently truncating oversized input.
3. Reuse `embedding_service` and multilingual-e5-small for actual normalized
   `passage:` and `query:` embeddings. Encode corpus chunks four at a time; cache
   only corpus vectors. The in-memory index has a content/config fingerprint and
   rebuilds on collection changes. User questions and answers are not persisted.
4. Rank chunks by cosine similarity, then rank messages by their best chunk score
   with a deterministic tie break. Preserve the matched span and original record.
5. For mailbox-wide tasks/calendar questions, all records in the bounded collection
   remain candidates, in learned ranking order. Deterministic evidence filters then
   select relevant source content. **This is exhaustive bounded filtering after
   ranking, not a top-5-only RAG context.** Good final evidence coverage can therefore
   coexist with imperfect Recall@5; neither measurement is substituted for the other.
6. Compose literal source excerpts with `[email_id=N]` citations, subject, sender
   and timestamp. Reuse `rag_evidence` and `rag_grounding` for supported literal
   field questions. Unsupported questions abstain and expose retrieved source
   passages for inspection. No prewritten question-answer lookup is used.

Existing pgvector retrieval in `semantic_search.py` is preserved for the private
Gmail application. It is unnecessary for a 24-message public collection. Its database,
ownership and OAuth paths are never imported by the showcase entry point.

## Temporal and related-message behavior

The collection is a fixed snapshot: **9 November 2026, 12:00 UTC**, displayed in
the UI. Week means Monday through Sunday relative to this date, not the visitor's
wall clock. Future-dated messages cannot change this snapshot's answers.

Thread IDs are curated provenance metadata, not inferred identity claims. A newer
explicit cancellation suppresses an older invitation and marks its task superseded,
linking the later source. The newest message provides a request's latest reported
status. An unspecified request spanning multiple threads prompts clarification.
Conflicting meeting dates are both cited; the composer does not invent a winner.

Dates come from explicit source fields or the existing deadline parser. Relative
task dates resolve against the message timestamp. Unparseable or conflicting
constraints stay ambiguous; missing deadlines remain missing. Overdue means a
stated date has passed, **not that the system knows the task is unfinished**.
There is no calendar account or external completion-state synchronization.

Supported question families cover meetings, interviews, reply requests, upcoming
deadlines, potentially overdue tasks and latest request updates. This is a bounded
rule-based query interpreter, not unrestricted natural-language reasoning. Extracted
Arabic/English text is quoted in its original language; it is not translated.

## Task extraction

`showcase.intelligence.task_records` reuses `task_extractor.extract_action_items`
and `deadline_extractor`. It attaches the original source line and offsets, message
ID, explicit named addressee/responsible field, deadline state, conditional-request
flag and cancellation evidence. It does not assume the sender is responsible.
The UI links each task to its original message and shows missing/ambiguous dates.

This is **deterministic NLP/rule extraction**, not a trained task classifier. Phase 2
did not obtain suitable action labels for training. Scores are rule strengths,
not calibrated probabilities. Quoted history, negative/completed instructions and
recognized embedded control-instruction text do not become new tasks.

The showcase never executes email instructions or tools. React renders source
content as text; the public answering path has no LLM whose instructions email
content could override. Control-like spans are excluded conservatively from
extraction/indexing and unsafe full sources from literal fallback. This pattern
filter is not advertised as a general prompt-injection detector or a proof that
every statement inside an email is true.

## Curated corpus and rights

`showcase/collection.json` has 24 original AI-authored fictional messages (15 English,
9 Arabic) covering interviews/applications, meetings, academic work, billing,
customer requests and travel. It includes conflicting proposals, cancellations,
conditional requests, absent/ambiguous deadlines and an adversarial instruction
fixture. All senders use reserved `example.invalid`; no personal mailbox, external
dataset or Google credential is used.

Authorship, reuse terms and the snapshot clock are recorded in
`showcase/provenance.json`. The original fixture text is dedicated to
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) to the extent copyright
applies. This does not relicense existing code, third-party models or earlier data.
The corpus is not representative of email prevalence, language varieties or real
sender behavior. It has not received independent human linguistic review.

## Frozen evaluation and actual results

The 20 questions (10 English, 10 Arabic), evidence IDs, expected statuses and task
labels were authored separately from the serving code/UI prompts before the Phase 3
composer was implemented, then frozen with corpus hashes. **The same AI assistant
authored the collection, implementation and labels. This is not an independently
human-authored or blind external holdout.** It is a frozen authored acceptance suite;
independent quality acceptance remains outstanding. No models were trained on it.

The suite ran once with real local E5 embeddings, no mocked inference, no Qwen and
no database. Failures were retained; no post-evaluation RAG/task tuning occurred.
Unit tests using fake vectors validate invariants only, not retrieval quality.
The complete machine-readable receipt is [benchmark-v1.json](benchmark-v1.json).

| Measure | Overall | English | Arabic |
|---|---:|---:|---:|
| Recall@1, answerable questions | 0.4286 | 0.4286 | 0.4286 |
| Recall@3 | 0.7500 | 0.7857 | 0.7143 |
| Recall@5 | 0.7619 | 0.7857 | 0.7381 |
| Recall@10 | 0.8214 | 0.8571 | 0.7857 |
| MRR | 0.7619 | 0.7619 | 0.7619 |
| nDCG@5 | 0.6990 | 0.7166 | 0.6813 |
| Exact cited evidence-set match | 18/20 | 9/10 | 9/10 |
| Citation precision against expected IDs | 0.9688 | 0.9412 | 1.0000 |
| Expected response-status match | 20/20 | 10/10 | 10/10 |
| Missing-evidence abstention | 6/6 | 3/3 | 3/3 |
| Warm answer p50 / p95, ms | 50.14 / 71.95 | 50.15 / 72.49 | 50.14 / 71.08 |

Recall is fraction of all labelled evidence found within k, averaged over the 14
answerable questions. MRR is first relevant message reciprocal rank; nDCG uses
binary relevance. Citation precision counts citations against frozen expected IDs.
The mechanical grounding check passed on cited answers: quoted lines are present
in sources and derived dates match the deadline parser. **That is not independent
semantic entailment or proof of complete answers.** Status correctness also does
not imply the evidence list is complete.

Task evaluation: 16 messages, 12 labelled tasks (six English, six Arabic), 12 true
positives, zero false positives and zero false negatives. Precision/recall/F1 were
1.0 on this small fixture suite; matched deadline, owner and source-reference checks
also passed. Four negative messages were English; their false-task rate was 0/4.
**Arabic negative-message false-task rate is unavailable**, because this frozen task
subset includes no Arabic negative message. Negative Arabic cases exist in unit
tests but do not fill this evaluation gap. These numbers are not deployment-grade
task accuracy or broad multilingual coverage.

### Retained failures

1. `q09`, deadlines strictly *after* the snapshot date: the implementation includes
   one task due *on* the reference date (message 19). Its date is source-derived,
   but the temporal boundary is broader than the question's expected scope.
2. `q10`, Arabic overdue tasks: message 6 is omitted. Its source line contains both
   a positive request and a negative instruction; conservative line-level rejection
   removes the whole line. The task-evaluation subset did not include message 6,
   which is why its perfect fixture scores must not be generalized.

Ranking is also imperfect, particularly for multi-evidence deadline lists. These
failures are preserved as findings, not relabelled away. A subsequent authorized
improvement should use new development cases and a new independently authored
evaluation; this suite is now consumed evidence.

## Runtime and Render feasibility

Measured Windows x64 CPU environment: Python 3.11.9, Torch 2.13.0 (CPU build),
Transformers 5.14.1, sentence-transformers 5.7.0, NumPy 2.4.6, tokenizers 0.22.2,
sentencepiece 0.2.2, FastAPI 0.141.1, uvicorn 0.52.4, Pydantic 2.13.5,
BeautifulSoup 4.15.0 and geonamescache 3.0.0. Evaluation uses psutil 7.2.2.
See [runtime.json](runtime.json). The E5 cache's actual revision and file hashes
were verified against the Phase 2 manifest:
`614241f622f53c4eeff9890bdc4f31cfecc418b3`.

No new dependency replacement is made. Existing full/local requirements provide
these AI dependencies; the existing minimal Render requirements do not provide
the complete Torch/E5 stack and were deliberately not changed. ONNX Runtime is
still required for the separate Email Intelligence feature, not Ask/tasks.
llama-cpp-python is not required or loaded by the public Phase 3 paths.

Cold model/index initialization took **66.96 seconds**. Peak Windows process working
set and final RSS were **880.27 MiB** for this Ask evaluation, without the classifier
or Qwen. Timings are local serial observations, not Render p95 guarantees.

[Render's current compute documentation](https://render.com/docs/compute-plans)
lists Free as 0.1 CPU / 512 MB. **This measured configuration does not demonstrate
a fit and exceeds that budget locally; it is NO-GO for Render Free as implemented.**
Removing Qwen does not solve the E5/Torch memory requirement. Adding Qwen cannot be
claimed safe on this allocation, so no additional combined-model benchmark or
hosting experiment was launched. Larger Render instances exist, but no purchase,
plan change or paid deployment is authorized or performed. Linux target capacity
remains unmeasured; a Windows process measurement is not a Linux certification.

## Reproduction and verification

Provision the verified E5 snapshot in the local HF cache, then set offline flags:
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `TOKENIZERS_PARALLELISM=false`,
`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`. No `.env` with Gmail/DB credentials.
Model files are never downloaded by a request. Use the Phase 1 local server command
after `npm run build:showcase` from `frontend`.

```sh
python -m pytest --confcutdir=showcase showcase/tests -q
python -m showcase.evaluation.run --output results/new-phase3-evaluation.json
# frontend, with the local server running on 127.0.0.1:4181:
node scripts/check-phase3.mjs
node scripts/check-showcase.mjs
```

The evaluator refuses an existing output path and changed frozen inputs. Reproducing
the run does not turn the consumed questions into a fresh holdout. Raw model artifacts
remain local; committed benchmark inputs/answers contain only the fictional corpus.

Final automated evidence: 38 showcase/backend tests, 180 frontend tests, typecheck,
lint and showcase build passed. Non-failing existing Starlette/httpx and Rollup
annotation warnings remain. Browser evidence and final checks are recorded in
`verification.json`. UI colors/components and Arabic RTL are preserved.

## Remaining boundaries

Independent human-authored/reviewed QA and action evaluation is still required,
including Arabic negatives, natural unstructured dates, paraphrases, quotes,
timezones and larger related threads. The two frozen-suite failures remain open.
Model capacity under the approved free hosting allocation remains a deployment
blocker. Phase 2 classifier quality failures are unchanged. This phase does not
claim production approval, deploy, replace model weights, or begin another phase.
