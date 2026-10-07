# AI Smart Inbox

For current setup, see [Production backend architecture](#production-backend-architecture).
Older AI-phase backfill/evaluation instructions below are operator-only tools; do not
run them as part of backend migration or expose them through HTTP.

AI Smart Inbox is a student portfolio MVP built with FastAPI. It connects to Gmail,
cleans email content, and uses a fine-tuned DistilBERT model to classify messages.

## Features

- Google OAuth login with read-only Gmail access
- Account-owned, paginated initial Gmail sync and incremental history sync
- Extract each email's ID, sender, date, subject, and body
- Extract and clean plain-text and HTML email content
- Multi-label email classification using DistilBERT
- Process multiple emails and continue when one email fails
- Return total, successful, and failed message counts
- API tests, including mocked Gmail and OAuth tests

The model was trained for multiple labels. The current API returns only the
highest-scoring category in the `predictions` list, with its model confidence score.
That score is not a guarantee that the classification is correct.

## Categories

- Business
- Customer Support
- Events & Invitations
- Finance & Bills
- Job Application
- Newsletters
- Personal
- Promotions
- Reminders
- Travel & Bookings

## Project structure

```text
text-classification-finetuning/
├── main.py                   # FastAPI app
├── routes.py                 # API endpoints
├── schemas.py                # Request validation
├── gmail_auth.py             # Google OAuth setup
├── gmail_service.py          # Gmail API client
├── email_utils.py            # Email extraction and cleaning
├── predict.py                # Model predictions
├── app.py                    # Model training
├── evaluate.py               # Model evaluation
├── test_main.py              # Basic API tests
├── test_gmail.py              # Mocked Gmail API tests
├── test_oauth.py              # OAuth tests
├── test_email_processing.py   # Cleaning and prediction tests
├── test_training.py          # Training helper tests
├── requirements.txt
├── .gitignore
├── README.md
└── results/                  # Local model files (ignored by Git)
```

## Installation

Use the existing Python 3.11 project environment. From the project folder:
For Windows PowerShell:

```powershell
.\env\Scripts\python.exe -m pip install -r requirements.txt
```

### Model setup

The default model is loaded from `results/checkpoint-3159`. This directory must
contain the saved model weights, configuration, and tokenizer files. Model weights
are not included in Git, and installing requirements does not download this checkpoint.

To use another compatible local model, set its path before starting the app:

```powershell
$env:EMAIL_MODEL_PATH = "C:\path\to\your\model"
```

### Gmail setup

1. Enable the Gmail API in your Google Cloud project.
2. Configure your OAuth consent screen and a web application OAuth client.
3. Register this redirect URI exactly:
   `http://localhost:8000/auth/google/callback`.
4. Save your OAuth client configuration as `credentials.json` in the project folder.
5. Complete the backend setup below, then authorize Swagger with an application bearer token.
6. Execute `POST /auth/google/start` in Swagger, then open its `authorization_url` in that same browser.
7. Complete consent. The callback stores encrypted credentials against the authenticated user/account.

If the OAuth app is in testing mode, your Google account must be an allowed test user.
Use `localhost` consistently when starting login and returning to the callback.

## Run the app

Run this command from the project folder:

```powershell
.\env\Scripts\python.exe -m uvicorn main:app --host localhost --port 8000 --no-access-log
```

API documentation: [Swagger UI](http://localhost:8000/docs).

## Main endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Check that the API is running |
| GET | `/auth/google` | Start Google login |
| GET | `/auth/google/callback` | Complete a one-use user-bound OAuth handshake |
| POST | `/gmail/messages` | Sync the only connected account; use the account-specific route otherwise |
| POST | `/gmail/accounts/{id}/sync` | Sync one owned account |
| GET | `/gmail/accounts` | List owned account metadata |
| DELETE | `/gmail/accounts/{id}/connection` | Disconnect, remove credentials, retain inbox |
| POST | `/auth/google/start` | Return consent URL and set browser nonce |
| POST | `/classify-email` | Classify a supplied subject and body |

Example request for `POST /classify-email`:

```json
{
  "subject": "Interview invitation",
  "body": "We would like to invite you for an interview on Monday."
}
```

`POST /gmail/messages` and the account-specific sync return `count`,
`success_count`, `failed_count`, `enrichment_failed`, `deleted`, and `emails`.
Success counts source storage, even if an enrichment stage fails. Empty syncs
return the same structure with zero counts. GET no longer triggers sync.

## Run tests

From the project folder:

```powershell
.\env\Scripts\python.exe -m pytest -q
```

Gmail tests use fake clients, isolated PostgreSQL transactions and synthetic OAuth
credentials. No live Gmail requests, real GGUF model or embedding downloads are
used. The existing classifier tests still require its local model files.

## Training and evaluation

These tools are separate from running the API:

```powershell
python app.py --output-dir results/email-candidate
python evaluate.py --model results/email-candidate --samples samples.json --output evaluation.json
```

Training cleans the data, merges duplicates, and uses separate training, validation,
and test splits. It saves a candidate model and `training_report.json` without
replacing the default model. The output directory must be empty.

Evaluation expects an `emails` list containing `subject`, `body`, and optionally
`expected_labels`. Accuracy is calculated only for examples with supplied labels.
For offline training, `app.py` also accepts `--dataset-file` and `--base-model`.

## Security

`credentials.json` and `token.json` are local secrets and must never be committed.
Both are ignored by Git. Do not share these files or paste their contents into logs.
Virtual environments, Python caches, pytest caches, and training outputs are also ignored.

The backend now has authenticated ownership boundaries and encrypted per-account
credentials. Deployment and browser login requirements are documented below.

## Current MVP status

The backend supports Gmail login, fetching and cleaning multiple messages,
classification, per-email error handling, and API tests. Classification quality
still needs evaluation on more real, labeled emails. Image-only emails may have
little or no body text when no useful image alt text is available.

## Tasks and deadlines

`extract_tasks(subject, body)` keeps the original task/confidence interface.
`extract_action_items(subject, body, reference_datetime=None)` adds nullable
deadline fields using the same task pipeline. No model, API, or dateparser is used.
Arabic/English obligations are filtered before timing is parsed. Deduplication
uses matching action families and object tokens; different identifiers or
different explicit constraints remain separate. At most five tasks are returned.

Supported timing includes Gregorian named months, ISO dates, weekdays, tomorrow,
month-end, explicit clock times, and event constraints such as before arrival.
Relative dates and missing years are anchored to the email Date header, never
the system clock. Weekdays mean the next occurrence (including the same day);
missing years mean the next occurrence of that month/day. Numeric dates such as
04/05/2026 and Hijri dates are not guessed. When several constraints occur in one
task, only the first is returned. Unresolved constraints remain readable text.
Date-only deadlines have no invented time. A timestamp requires an explicit
timezone or the email header's timezone; otherwise its date/text are retained.
Confidence is deterministic rule strength, not an ML probability.

`GET /emails` includes `deadline_text`, `deadline_date`, `deadline_at`, and
`deadline_confidence` for each task. `has_deadline=true/false` combines with
`category`, `priority_level`, and `has_tasks`. Existing matching tasks can receive
missing deadline fields during Gmail fetching without replacing saved tasks.

### Manual database update

Stop the app before applying the schema change. From the project directory,
using a working Python environment with the project's dependencies and the
intended `DATABASE_URL` configured:

```powershell
python -m alembic upgrade head
python rebuild_tasks_and_deadlines.py
python -m uvicorn main:app --reload
```

The rebuild replaces only task rows, in one transaction. It preserves email
bodies, summaries, predictions, priority, sender, and dates. Failure rolls back
the entire rebuild. It is manual and is never launched by the app.
The older task backfill and content-reprocessing scripts also use action items
so that they retain deadline support when explicitly run.

Tests use the separate `TEST_DATABASE_URL`; production connections are blocked
by the test fixtures. Upgrade only the test database before running tests with
the new schema. Production migrations and rebuilds are separate manual steps.

Rules can miss unfamiliar paraphrases or ambiguous context. Similar tasks with
different recipients are kept separate; full semantic understanding is not claimed.

## Semantic search

`GET /search/semantic?q=...&limit=10&min_score=0.7` searches indexed email chunks.
`q` must contain non-whitespace text (at most 4000 characters and 512 model tokens);
`limit` is 1–50. Optional `min_score` is -1–1. Results contain one email each,
the best chunk's score, and up to 2000 characters of matching text. Email bodies
and vectors are not returned; use `GET /emails/{id}` for the full stored message.
Scores are cosine similarities (`1 - cosine_distance`), not probabilities.

### Model and content

`embedding_service.py` lazily loads `intfloat/multilingual-e5-small` once per
process, using CPU unless `EMBEDDING_DEVICE` is set (for example, `cuda`). It adds
`query: ` / `passage: ` prefixes and validates finite, nonzero, normalized
384-dimensional vectors. Empty input and overlong inputs are rejected instead
of silently truncated. Imports and application startup do not load the model.
The first indexing/search operation that needs it may download weights.

`build_semantic_text` combines subject, cleaned summary, and
`extract_main_content(subject, body)`, suppressing repeated text and old summaries
that reintroduce excluded footer/tracking content. Stored email bodies are untouched.
Chunking uses the model tokenizer's character offsets, targets 300 tokens, prefers
nearby sentence/paragraph endings, and overlaps up to 40 tokens. Order and original
wording are preserved; very long sentences can cross chunk boundaries. This stays
below E5's 512-token limit including its prefix and special tokens.

Model requirements: [E5 model card](https://huggingface.co/intfloat/multilingual-e5-small).
Index integration: [pgvector SQLAlchemy documentation](https://github.com/pgvector/pgvector-python#sqlalchemy).

### Storage and transactions

Migration `f1a6b3c802de_add_email_embedding_chunks.py` follows pgvector activation
`e8f3a2b491cd`. It creates `email_embedding_chunks` with `vector(384)`, an email FK
with cascading deletion, and unique `(email_id, chunk_index, embedding_model)`.
The cosine HNSW index uses `vector_cosine_ops`, `m=16`, `ef_construction=64`.
Downgrade removes only the chunk table and its indexes; it keeps the extension.

`index_email` locks the parent email and uses a savepoint. SHA-256 includes chunk
text, model name, and the content/chunking version. Unchanged chunks skip encoding;
changed chunks are replaced and stale chunks/old model rows are deleted. It does
not commit. Bump `CONTENT_VERSION` if preprocessing/chunking behavior changes.

Gmail stores the source first, then indexes finalized **stored** content in an
independent savepoint within the account sync transaction. Indexing errors are logged without message contents and do
not turn a saved email into a failed email. A later sync/backfill retries missing
or outdated vectors. Existing classification, priority and task behavior is unchanged.
There is no startup backfill, queue, worker, LLM call or answer generation.

Search retrieves nearest chunks through pgvector, expands the candidate pool if
duplicates consume it, and keeps the highest scoring chunk per email. HNSW is
approximate; recall is not guaranteed, and thresholds need real-mail evaluation.
Results include only indexed emails for the current model. Encoding is synchronous
and CPU latency depends on hardware. Large backfills use a long transaction and
roll back the whole job on failure; the script prints progress and final counts.
Repeated syncs still tokenize content to check chunk hashes, but skip unchanged
embedding calls. There is no multi-user isolation beyond the current email model.

### Manual setup (do not run against production unintentionally)

From the project directory with a working Python environment and the intended
`DATABASE_URL` in `.env`:

```powershell
python -m pip install -r requirements.txt
python -m alembic upgrade f1a6b3c802de
python -c "from embedding_service import embed_query; v=embed_query('flight to Jeddah'); print('dimensions:',len(v),'norm:',sum(x*x for x in v)**0.5)"
python backfill_email_embeddings.py
python -m uvicorn main:app --reload
```

The model check is the first intentional model download/load. Ensure
`HF_HUB_OFFLINE` is unset for its first download. Run backfill only after migration
and model verification; it creates/updates chunks without changing email content.

```powershell
$q = [uri]::EscapeDataString('متى سفرتي لجدة؟')
Invoke-RestMethod "http://127.0.0.1:8000/search/semantic?q=$q&limit=10"
```

Tests replace the lazy model loader with deterministic embeddings and a fake
tokenizer. They never download/load the real model. The validated `_test` database
alone receives the extension/table setup; each test rolls back its data. Retrieval
tests prove wiring/ranking with controlled vectors, not real E5 retrieval quality.

## Local inbox Q&A (RAG)

The architecture is retrieval -> conservative evidence selection -> bounded escaped
context -> grounded prompt -> LLMProvider.generate -> citation validation -> POST /ask.
Retrieval finds evidence; generation answers using it. No schema migration or
backfill is needed for this change. No paid API is used.

### Low-memory Windows generation

RAG generation now uses **llama-cpp-python 0.3.35**, with its official Windows x64
CPU wheel (7.1 MB download), rather than FP32 Transformers weights. Its small
`diskcache` dependency is also required; NumPy, Jinja2 and typing-extensions are
already shared dependencies. `requirements-local.txt` is optional and forces
binary-only installation: it will fail rather than start a source build. Torch
and Transformers remain installed for embeddings/classification, not generation.

Selected model: `unsloth/Qwen3-0.6B-GGUF`, `Qwen3-0.6B-Q4_K_M.gguf`.
Pinned revision: `50968a4468ef4233ed78cd7c3de230dd1d61a56b`.
Size: **396,705,472 bytes** (396.7 MB / 378.3 MiB).
SHA-256: `ac2d97712095a558e31573f62f466a3f9d93990898b0ec79d7c974c1780d524a`.
Q4_K_M costs only ~13.4 MB more than the same repository's Q4_K_S while retaining
more precision in selected tensors. The official Qwen GGUF repository currently
lists Q8_0 (~639 MB); Unsloth provides the smaller Q4 options.
Sources: https://huggingface.co/unsloth/Qwen3-0.6B-GGUF/tree/main and
https://abetlen.github.io/llama-cpp-python/whl/cpu/llama-cpp-python/

Budget roughly **0.7–1.2 GiB additional RAM** for this small GGUF, its KV cache and
inference buffers at 2048 tokens (estimate, not a measured memory benchmark). Reserve **1.5–2 GiB
available RAM** for generation headroom, plus any embedding/classifier models not
yet loaded. Free RAM varied from ~1.75 to ~1.24 GiB during inspection; final free
disk was ~1.16 GiB. Close applications to restore memory headroom. Disk fits
the selected download plus margin, but RAM is marginal for the entire inbox app.
Close memory-heavy applications first. Model size alone is not a fit guarantee.
CPU speed depends on the processor and prompt length; no throughput claim has
been benchmarked. The later evidence-selection evaluation loaded the existing GGUF locally; no model was downloaded.

CPU defaults: 2048 total context tokens, 256 output tokens, two threads (one on
single-core machines), n_batch=n_ubatch=64, no GPU layers, mmap on, mlock off.
Loading and generation are locked; one provider and model per application process.
Use one uvicorn worker. The model loads only on the first generation request.
The tokenizer checks the FULL formatted prompt plus reserved output before
inference. RAG packs complete SOURCE blocks into that token budget automatically;
sources that cannot fit are dropped, without slicing facts or source boundaries.
If none fits, the application abstains without generation.

### Configuration

- RAG_PROVIDER=local
- RAG_MODEL_PATH: direct GGUF path; default `<project>/local_models/Qwen3-0.6B-Q4_K_M.gguf`
- RAG_CONTEXT_SIZE=2048 (512–8192; total prompt + output)
- RAG_MAX_NEW_TOKENS=256 (32–1024, less than context size)
- RAG_THREADS=2 (1–32)

Restart after changing configuration. RAG_MODEL and RAG_MAX_INPUT_TOKENS from the
old Transformers adapter are no longer used. There is no Hugging Face cache lookup
or network operation in local_llm.py. The adapter uses Qwen3's non-thinking ChatML
prompt with the empty thinking block prefilled; greedy decoding, fixed seed,
and no streaming. Tagged reasoning is removed; incomplete thinking tags fail
closed rather than exposing reasoning. Untagged unwanted reasoning remains a
model quality limitation; strict citation validation still applies afterward.
Larger **Qwen3-compatible ChatML GGUF** models can be selected by RAG_MODEL_PATH
without touching rag_service. Other model families need their correct prompt
adapter; changing a filename does not make incompatible templates interchangeable.

### Explicit setup (no automatic downloads)

Run from this project directory using the project virtual environment.
No alternate interpreter or PYTHONPATH override is needed.

```powershell
$py = '.\env\Scripts\python.exe'
# Already installed during implementation; required only when setting up again.
& $py -m pip install --no-cache-dir --only-binary=:all: -r requirements-local.txt
& $py -m pip check
# Downloads ONLY the pinned GGUF, explicitly; never run by app startup or tests.
& $py download_rag_model.py
# Optional alternate drive: use --destination 'D:\Models\Qwen3-0.6B-Q4_K_M.gguf'
# and set RAG_MODEL_PATH to that same path before starting the app.
$env:RAG_PROVIDER = 'local'
$env:RAG_CONTEXT_SIZE = '2048'
$env:RAG_MAX_NEW_TOKENS = '256'
$env:HF_HUB_OFFLINE = '1'  # Also keep the already-cached embedding model offline.
& $py -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The download script checks **file size + 512 MiB disk safety margin** before any
model transfer (~890 MiB required). It streams to one temporary file on the target
drive, verifies exact size/SHA-256, and publishes without overwriting existing
files. A matching existing file is verified and reused without network access.
A mismatching destination fails safely. Only its own partial file is removed on
failure. No cache/user files are deleted. The target filesystem must support hard
links (NTFS does). The pinned download can be saved anywhere; other models should
be obtained separately and selected by RAG_MODEL_PATH.

### API and real evaluation

`POST /ask` takes question (1–2000 characters), chunk_limit (1–20, default 4),
max_chunks_per_email (1–5, default 2), optional min_score (-1 to 1), and
max_context_chars (1000–12000, default 6000). Response: answer, status, citations,
sources with email/chunk IDs, score, subject, sender and date. No full body or
embeddings. In a second PowerShell window:

```powershell
$questions = @('متى سفرتي لجدة؟', 'When is my flight to Jeddah?', 'ما الفواتير المطلوب سدادها؟', 'What is my submarine booking number?')
foreach ($q in $questions) {
    $json = @{question=$q; chunk_limit=2; max_context_chars=2500} | ConvertTo-Json
    Invoke-RestMethod 'http://127.0.0.1:8000/ask' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($json)) | ConvertTo-Json -Depth 8
}
```

Compare answers to cited source emails. Test Arabic, English, invoice/registration
deadlines, missing evidence and a synthetic injected email; one travel query is
not sufficient evaluation. A 0.6B quantized model can misunderstand Arabic,
produce unsupported facts or fail the required citation format. This change
reduces resource requirements, not these accuracy limitations. See the evidence-selection
evaluation below for subsequent real-model checks; no systematic memory benchmark was run. Generation is synchronous without a
hard cancellation SLA; keep questions/context short on this machine.

### Security and privacy

Emails remain untrusted, source fields escaped, and prompts grounded. Each answer
paragraph must cite an ID in the retrieved set. Citation validation verifies
membership, NOT sentence-level entailment or perfect injection resistance.
No context -> fixed Arabic/English insufficient-evidence response without model
loading; exact INSUFFICIENT_EVIDENCE also maps to that response. Invalid/empty,
uncited and foreign-citation output is discarded and returns a safe application
abstention (HTTP 200). Actual backend failures return sanitized 503 responses.
No question/source logging, tools, actions, hosted generation, billing or telemetry
are added. Only the manual model download contacts Hugging Face; inbox data never
leaves the machine through this provider. Keep the API bound to localhost. Bearer
authentication and OwnedSession enforce ownership in every retrieval query before
ORDER BY and LIMIT; source/citation checks remain additional safeguards.

### Tests

`python -m pytest -q` and `git diff --check`.
Fake backends test loading once, concurrency, CPU settings, missing files, bad
configuration, failures, context limits and reasoning suppression. Download tests
use in-memory fake responses only. Arabic Unicode and question preservation are
asserted directly from Python. Existing retrieval, citations and API tests remain.
No test loads/downloads a GGUF, calls the network or requires llama.cpp installed.

### Evidence selection and local quality evaluation

`rag_evidence.select_evidence` sits between retrieval and context construction.
It recognizes repeated short `label: value` fields as record boundaries and keeps
all subsequent lines attached to each record. Compound pipe-separated summary
lines are not record anchors. Only original spans are used; no facts or labels
are invented. Shared introductory context is retained. Query constraints can
select records by an explicit to/from/for relationship or a distinguishing term
(person, version, item name, etc.). Arabic normalization handles spelling/diacritics
and the attached to/for preposition. This is a limited lexical selector, not a
translator, parser of arbitrary prose, or inference engine.

If record structure is absent, no qualifier matches, all records match, or the
question requests a comparison/list/coordinated targets, original chunks are
preserved. Other retrieved chunks are also preserved for adjacent or multi-part
answers. Selection records original character offsets for debugging. Retrieval
scores/order, stored chunks/vectors and schema are unchanged; no backfill/migration
is required. Citation enforcement and untrusted SOURCE escaping remain unchanged.

This design was chosen after reproducing a wrong date with a valid citation.
Separating records without selecting evidence did not fix it; E5 also ranked the
wrong direction slightly higher. Therefore semantic similarity alone is not used
to decide between almost identical records. Scope is resolved only when a clear
lexical relation/qualifier is present. The selector reduces one source of confusion
but does not prove that generated claims are entailed by the selected evidence.

Limitations: this targets explicitly labelled records, not arbitrary prose/tables.
Cross-language entity aliases are not translated. Relation matching is lexical,
not full syntax/negation understanding; ambiguous and unsupported wording can
remain unresolved. Common multi-word entity prefixes may retain several records.
Unknown formatting and shared trailing text can limit record-boundary accuracy.
Other retrieved chunks can still contain distractors. The existing local token
budget can reject long multi-source requests. The small generator still sometimes
abstains despite available evidence or emits an invalid fallback format, which
continues to be rejected rather than relaxing validation.

Reproduce locally (read-only DB; cached models only; no email output files):

```powershell
$env:RAG_MODEL_PATH = 'D:\AI-Models\Qwen3-0.6B-Q4_K_M.gguf'
.\env\Scripts\python.exe evaluate_rag.py --question 'متى سفرتي لجدة؟'
.\env\Scripts\python.exe evaluate_rag.py --chunk-limit 1 --question 'متى سفرتي لجدة وما وقت المغادرة؟'
.\env\Scripts\python.exe -m pytest -q
git diff --check
```

`evaluate_rag.py` accepts repeated --question arguments. It reports retrieved IDs
and scores, evidence offsets/reasons, raw generation, and citation-validation status
separately. JSON uses Unicode escapes for Windows consoles. --show-evidence prints
private selected context only when explicitly requested. Generation uses the same
service and validation as /ask. Factual correctness must be checked against the
original source; passing citation checks is not a factual accuracy score.


Latest local evaluation (not a general accuracy guarantee): the original Arabic
trip-date question initially returned the other record's date; with evidence
selection it returned the correct date and valid citation, including with the
four-chunk API defaults. Event date and application-status questions also worked.
The model still confused arrival with departure time within the correct record,
abstained incorrectly on a registration deadline/reference question, and produced
noncanonical insufficient-evidence output rejected by citation validation. Some
longer four-chunk requests hit ContextTooLarge. These are remaining failures,
not passing results. An additional prompt instruction was tested and discarded
because it worsened citation compliance without fixing the time confusion.

### Persisted structured facts (facts-v1)

The Hybrid engine now has a stored facts layer. It still identifies sources through
semantic retrieval and evidence selection. It then reads current facts for those
emails, checks that their literal evidence occurs in the selected content, and
attempts a unique direct lookup. A successful lookup returns literal values and
citations without loading/calling GGUF. Ambiguous, unsupported, comparative and
free-form questions use the existing local generation path. Both paths use the
same citation validation and the `/ask` response fields are unchanged.

`email_facts` stores email ID, normalized role, original label and value, optional
normalization metadata, exact text and character offsets in the stored body,
record boundaries, extraction reason/version, and timestamps. Facts are independent
of embedding chunk lifetimes; a selected chunk is associated at query time. A unique
email/fact key prevents duplicates and an email/role index supports scoped reads.
`email_fact_states` records the input hash and extractor version, including emails
with zero facts. Both tables cascade when their parent email is deleted. This
normalized design permits individual fact provenance without a new schema for each
business domain; only heterogeneous normalization details use JSONB.

Extraction reuses main-content selection, the existing labelled-field parser and
deadline/calendar grammar. Supported structures include short `label: value`
fields, vertical identifier fields, and explicit deadline/last-day expressions.
No summary or model-generated scalar is authoritative. No company, sender, city,
email ID or benchmark-specific parser is used. A time colon cannot start a field.
Each fact must map uniquely back to exact literal evidence in `Email.body`.
Cleaning transformations or repeated identical evidence can therefore reduce recall.

Normalization preserves the literal value. Explicit ISO/named-month dates become
date-only ISO values; ambiguous numeric dates remain unnormalized. A missing year
is inferred only for a named day/month within 45 days of the message timestamp in
the same year and with an explicitly matching weekday. That basis is recorded;
otherwise the year remains unknown. Message timestamps are never copied as event
dates. Times accept explicit clocks and optional UTC/GMT/offsets; absent timezone
stays null and no midnight is invented. Simple decimal amounts preserve explicit
currency text without interpreting ambiguous separators or dollar symbols as USD.
Identifiers/statuses retain literal spelling. Date answers show the literal date
with its normalized ISO value where available.

The hash covers subject, stored body and message timestamp. An unchanged hash and
extractor version skip extraction and rewrites. Changed inputs/version replace or
remove stale facts atomically under a parent-row lock and savepoint. A failed refresh
keeps the previous rows, but the read path rejects stale hashes/versions and invalid
source spans. Bump `EXTRACTOR_VERSION` when extraction semantics change, or use
`--force` to refresh explicitly. This freshness check covers facts; it does not
rebuild or certify old embedding chunks.

Gmail ingestion stores the source first, then uses independent savepoints for fact
extraction and semantic indexing before committing the account sync transaction. A fact failure logs only email ID/error class and cannot
discard the email or prevent the subsequent indexing attempt. Backfill retries
failed emails and commits each successful email separately, with bounded ID batches
and created/updated/skipped/deleted/failed counts. It changes only facts/checkpoints.

#### Activation and backfill

The new migration is `a2b7c4d913ef`, after `f1a6b3c802de`. Historical migrations are
unchanged. Its downgrade removes only the two new tables. Production migration and
backfill are manual. From the project directory, with `DATABASE_URL` selecting the
intended database:

```powershell
.\env\Scripts\python.exe -m alembic upgrade head
.\env\Scripts\python.exe backfill_email_facts.py                 # read-only preview
.\env\Scripts\python.exe backfill_email_facts.py --apply         # persist facts
.\env\Scripts\python.exe backfill_email_facts.py --apply --force # explicit rebuild
```

`--batch-size` accepts 1–500 (default 100). Dry run is the default and sets a PostgreSQL
read-only transaction; it reports discovered counts, not predicted insert/update counts.
If email bodies are later reprocessed, rerun this backfill. Missing facts tables
leave existing Hybrid behavior available until migration; ingestion logs failed
fact writes safely. No new environment variables or dependencies are required.

#### Privacy, evaluation and limits

Facts are local untrusted data, never instructions. Reads are restricted to already
retrieved email IDs and facts evidenced inside selected SOURCE text. This preserves
the existing trusted local boundary; future multi-user support must authorize
retrieval by owner first. No external inference, telemetry, email-body logs, model
downloads or new prompt tools are introduced.

```powershell
$env:HF_HUB_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:RAG_MODEL_PATH = 'D:\AI-Models\Qwen3-0.6B-Q4_K_M.gguf'
.\env\Scripts\python.exe evaluate_rag.py --preview-facts --chunk-limit 1 --question 'متى سفرتي لجدة؟'
.\env\Scripts\python.exe -m pytest -q
git diff --check
```

Evaluation always uses read-only DB access. `--preview-facts` runs the same extractor
in memory, so real inbox evaluation can precede migration/backfill. Omit it to
evaluate persisted facts. Reports distinguish discovered facts, resolver output,
LLM calls, raw/final answers, citations and timings; JSON escapes Unicode for Windows.
These reports contain private extracted values: keep them local. Selected full
content is shown only with `--show-evidence`.

Precision is preferred to recall. City/time position alone never establishes
departure/arrival roles. Unlabelled prose, cross-language aliases, broad paraphrases,
relative dates, complex amounts and implicit relationships may remain unresolved.
Clear same-record multi-value lookups are supported, including plural times/dates;
conflicts or uncertain qualifiers fall back. Retrieval still uses cached E5; the
deterministic path skips GGUF, not the source-identification step. Generative fallback
can still confuse roles or abstain incorrectly, and citation membership does not
prove factual correctness. Stored facts do not make the small model reliable for
every factual question.

Latest facts-phase check (2026-10-03): 745 tests pass using isolated PostgreSQL.
Read-only real-inbox preview with Qwen3-0.6B and one retrieved chunk resolved the
booking reference and Arabic registration deadline without GGUF (about 37 ms and
117 ms after retrieval warm-up). Trip date, event date and application status still
used generation successfully; unsupported booking correctly abstained. Departure
time remained wrong in generation, and arrival-time retrieval selected an unrelated
email. Therefore this is a useful persistence baseline with important extraction
and retrieval gaps, not a claim of reliable general factual answering. Production
migration/backfill were not applied during this evaluation.

### Relational facts and RAG candidate ranking (facts-v2-relations)

The next version reuses `email_facts` and its checkpoints; no schema migration or
embedding reindex is needed. Original facts retain their keys and IDs. In addition
to labelled scalars, extraction recognizes a directed route (`from A to B`, Arabic
equivalents, separate From/To fields, or `A → B`) with clock rows explicitly naming
the same endpoints. A directed clock pair can accompany a directed route. Labels
such as Departure/Arrival or Start/End can also introduce a clock on the following
line. Two isolated clocks never establish roles. Matching endpoints, not row order,
decides departure versus arrival; duplicate endpoint clocks, conflicting labels,
conditional/cancelled groups and incomplete groups are rejected conservatively.

Derived facts contain origin, destination, departure time and arrival time where
proved. The existing JSONB normalization metadata also carries endpoint names and
ordered literal proof anchors. Source offsets still point into the stored body;
the derived source label names the assigned role and the extraction reason explains
its origin. If main-content selection removes a short heading, a complete directed
route and its named clock rows can still prove the relationship. Every proof anchor
must remain in order within one selected record. Records/chunks cannot contribute
unrelated fragments to manufacture a relationship. The cleaner and stored chunks
are unchanged. Clock colons no longer create false record boundaries.

RAG now unions E5 candidates with a separate persisted-role candidate query before
reranking. The vector pool still starts at max(50, 10 × limit), expanding only for
per-email diversity up to 1000. The role path selects at most 64 chunks (plus one
overflow sentinel), ordered by semantic distance within emails containing the
requested role. It uses a correlated EXISTS lookup and the existing email/role
and chunk/email indexes. Candidate sources are merged by chunk ID using reciprocal
rank fusion (constant 60); raw cosine is never added to a binary role signal.
Current, provenance-validated role/qualifier matches form the first ranking tier.
Unvalidated role nominations receive no authority over semantic nonmatches.
Stale facts, absent proof anchors and ambiguous records still cannot resolve an
answer. Saturated role lookups abstain for scalar intents rather than claim
uniqueness from an incomplete pool. The returned `score` remains cosine similarity.
Minimum cosine filters and ownership apply inside SQL before sort/LIMIT. Final
per-email caps and requested limits apply after reranking. No embedding backfill,
schema change, lexical full-table body search or sender-specific rule is used.
`/search/semantic` retains its existing purely semantic behavior; this ranking is
specific to RAG source selection.

### Scaling limits and token packing

`POST /ask` retains its defaults: 4 chunks, at most 2 per email, 6000 context
characters. Characters remain an additional transport cap, not a token estimate.
Only the generative path loads the GGUF vocabulary (`vocab_only=True`, no model
weights) to count the exact escaped ChatML prompt. It reserves the configured
output budget (256 tokens by default) and 32 safety tokens within the actual
2048-token context. Once generation loads the model, its tokenizer is reused.
Deterministic facts bypass both tokenization and generation.

Packing preserves ranked complete sources and skips lower-priority blocks that
do not fit. A single oversized block may be omitted entirely: this intentionally
prefers abstention over truncating a negation, relationship or structured record.
The backend retains its final token guard. Model output failing citation checks,
empty output, incomplete reasoning tags or overflow are discarded. HTTP 422 is
still appropriate for invalid request fields or an oversized embedding question;
ordinary excess retrieved evidence does not cause it. Provider initialization or
execution failures remain 503. Citation membership is not factual entailment:
a small model can still produce a wrong answer with a valid citation.

Candidate results expose internal counts, source ranks and stage timings for
local evaluation, without changing the public response. Work is bounded in Python
by candidate limits; database work can still grow with the number of matching
role-bearing emails. Broad role queries may saturate and abstain. Literal place
qualifiers do not translate place names between languages. No global lexical
body scan or second email index was added: persisted roles identify candidate
emails, and their existing chunks supply semantic relevance and proof. More
indexes should be justified with query plans at the target workload.

On the measured local corpus (~3,900 emails), the role query used existing
indexes and examined four candidate chunks, taking about 1 ms in a warm SQL
EXPLAIN ANALYZE. The vector plan instead traversed the owner's chunk rows and
sorted cosine distances (~28 ms SQL); HNSW existence does not guarantee planner
use. Do not assume sublinear vector-search scaling from these measurements.
Three-run end-to-end retrieval medians (including query encoding) were roughly
0.39–0.70 seconds after the change. A small seven-target check improved Recall@4
from 6/7 to 7/7, but supported questions still sometimes receive safe false
abstentions from the 0.6B model. This is not a claim of general answer reliability.

`fact_roles.py` supplies a small bilingual vocabulary for departure/arrival,
start/end, origin/destination, travel dates, and time/date. It supports direct questions such as
`What is the arrival time?`, `متى المغادرة؟`, and `وش وقت الوصول؟`. Literal direction,
subject/sender, date and reference qualifiers narrow candidates. Different matching
emails/records remain ambiguous even when their values coincide: the service returns
insufficient evidence when the candidate pool reveals a conflict, including when
`chunk_limit=1` would hide a second candidate. Otherwise an unresolved lookup follows
the existing generation path. Citations, SOURCE escaping and `/ask` fields remain
unchanged. Generic explicit old/new fields keep their existing resolver behavior.

Upgrade existing facts using the same safe workflow:

```powershell
.\env\Scripts\python.exe backfill_email_facts.py
.\env\Scripts\python.exe backfill_email_facts.py --apply
.\env\Scripts\python.exe backfill_email_facts.py --apply
```

The first command is read-only preview; inspect it before applying. The last command
should skip unchanged facts. This phase verified all original 34 keys/IDs/values and
source spans before and after local application: 8 created, 34 version updates,
0 deleted, 0 failures; final totals 42 facts and 89 checkpoints. Repeat application
created/updated/deleted zero rows and skipped 42 facts across 89 unchanged emails.
No email bodies, summaries, tasks, vectors or schema were rewritten.

Current limits: the bounded candidate pool can miss a relevant email; lexical
qualifiers are not general translation/entity resolution; unusual tables, multi-leg
routes, timezone conversions, indirect wording and broad paraphrases may remain
unresolved. Relation groups are bounded to 20 nonempty lines / 1000 characters.
Main-content filtering can still omit structures. A supported direct lookup bypasses
GGUF; a free-form/unsupported question can still reach the imperfect generator.
Authorization now uses mandatory owned request sessions; SQL candidate filtering
precedes fact-aware ranking. Operator evaluation scripts remain privileged tools.

Validation for this phase: 792 isolated PostgreSQL tests pass, including generic
relational structures, contradiction/ambiguity, record boundaries, qualifier-aware
ranking, literal provenance, version refresh, and existing security/API regressions.
The local 8-case persisted evaluation resolved both departure (11:35) and arrival
(13:25) deterministically, preserved the booking/deadline successes, and correctly
abstained on the unsupported question. All 8 expected outcomes passed in this small
evaluation; it is not a general accuracy guarantee. The Arabic travel-date paraphrase,
event date and application-status question still used the generator. No model
benchmarking or prompt tuning was performed.


## Production backend architecture

### Ownership and authentication

`AppUser -> GmailAccount -> Email -> predictions/tasks/chunks/facts/checkpoints`
is the ownership path. One user may connect multiple Gmail accounts. A normalized
Google mailbox address belongs to one application user; reconnect cannot transfer
it. Email identity is `(account_id, message_id)`, enforced by PostgreSQL.

Application authentication uses 256-bit random, revocable bearer tokens. Only their
SHA-256 hashes and UTC expiry are stored. Tokens expire after 7 days by default
(maximum 30). They are issued through the operator CLI, not a public registration
endpoint. A numeric user ID/header/query parameter is never authentication.
Gmail consent grants mailbox access; it does not log a user into the application.

Every data route uses `get_db`, which creates a fresh `OwnedSession` bound to the
verified principal. Central SQLAlchemy criteria cover accounts, credentials,
emails and every email child, including aliases, counts and column projections.
Vector candidates are filtered in SQL before ORDER BY/LIMIT and fact-aware
ranking. Context construction reloads source IDs through that same boundary;
existing citation validation permits only the resulting source set. Core/raw SQL
and bulk request-session writes are rejected, apart from fixed internal catalog,
vector-settings and advisory-lock statements. Flush checks prohibit cross-owner
parents and ownership reassignment. New mapped types must join this policy before
request sessions can use them.

`SessionLocal` is privileged and restricted to authentication/OAuth control-plane
operations and operator scripts. Never introduce it into data routes. This is an
application boundary, not PostgreSQL RLS or protection against arbitrary trusted
server code/DB administrator access. Do not use the current local superuser DB
role for deployment: use a dedicated limited runtime role and a separate migration
role. DB role provisioning, TLS, host/backup encryption and OS access controls are
operational setup, not performed automatically by this migration.

### OAuth and token storage

Only `gmail.readonly` is requested. Start requires application authentication;
callback uses a server-stored, ten-minute, one-use state plus browser-bound nonce
and encrypted PKCE verifier. The nonce cookie is HttpOnly, SameSite=Lax, path-bound,
and Secure with HTTPS. State is consumed before token exchange. Callback reads
Google's mailbox profile, rejects accounts belonging to another user, and stores
credentials encrypted in `oauth_credentials`. No token is returned in API JSON.

`OAUTH_TOKEN_KEYS` is a comma-separated Fernet key ring, newest key first. Fernet
provides authenticated encryption; `v1:` identifies the storage format. Invalid
keys/ciphertext fail closed. To rotate, add a new key first, run the operator
`rotate-encryption` command, allow outstanding ten-minute OAuth handshakes to
expire, then retire the old key only after verifying backups/recovery requirements.
Refreshes (including automatic mid-sync refreshes) persist encrypted credentials.
Missing refresh tokens on reconnect retain the existing account token; first-time
connections without an offline token are rejected. Revoked credentials require
reconnect. Disconnect deletes local credentials and keeps the inbox; Google-side
revocation remains available in the user's Google account settings.

`token.json` is not read or written by the application. Keep any legacy copy
protected until reconnection is verified; delete/revoke it manually afterward.
No automatic import or identity guessing is performed.

### Configuration and manual activation

New settings:

| Setting | Meaning |
|---|---|
| `OAUTH_TOKEN_KEYS` | Required for OAuth/token use; secret Fernet key ring |
| `GOOGLE_CLIENT_FILE` | OAuth client JSON path; defaults to `credentials.json` |
| `GOOGLE_REDIRECT_URI` | Registered callback; defaults to loopback development URL |
| `APP_ENV` | `development` permits loopback HTTP only; use `production` with HTTPS |

Existing `DATABASE_URL`, `TEST_DATABASE_URL`, model/embedding settings remain.
There is no hardcoded model path. No `.env` or real secret files were modified.
Configuration errors never return secret values. Wildcard CORS and debug mode are
not enabled. The ASGI middleware removes query strings from the server access-log
scope while preserving request parsing. Also disable/sanitize proxy access logs:
OAuth codes and semantic queries must not be logged outside the application.

**Local database activation is intentionally manual.** Existing mailbox ownership
has not been verified. Before running these steps, stop the old app, verify that
`DATABASE_URL` names `ai_smart_inbox`, and explicitly identify who owns its legacy
mailbox. Do not infer ownership from message senders.

1. Back up the intended database using your configured PostgreSQL credentials:

   ```powershell
   pg_dump -h localhost -U postgres -d ai_smart_inbox -Fc -f ai_smart_inbox_before_backend_hardening.dump
   ```

2. Apply the migration (no backfill/reprocessing commands are required):

   ```powershell
   .\env\Scripts\python.exe -m alembic upgrade b3c8d5e024fa
   ```

   All existing emails move to a disabled `legacy-quarantine` user/account. IDs,
   bodies, predictions, tasks, vectors, facts and provenance stay intact. Raw
   `email_date` stays intact; safely parsed headers populate `sent_at`. Invalid,
   absent and timezone-less headers receive `invalid`, `missing` or `naive` status;
   no date/timezone is guessed. `message_at` remains NULL until Google supplies it.
   Downgrade is allowed only before any account leaves quarantine; once real
   accounts exist it refuses rather than discard ownership.

3. Generate a key locally and store it in untracked `.env` as `OAUTH_TOKEN_KEYS`:

   ```powershell
   .\env\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   .\env\Scripts\python.exe backend_admin.py create-user --name local-owner
   ```

   Store the displayed application bearer token securely. Do not paste it in
   source, tickets or logs. `issue-token --user-id <id>` issues another token;
   `revoke-tokens --user-id <id>` revokes all tokens for that user.

4. Start the app using the project interpreter:

   ```powershell
   .\env\Scripts\python.exe -m uvicorn main:app --host localhost --port 8000 --no-access-log
   ```

   Open `/docs` on that same hostname, use **Authorize** with the application token,
   execute `POST /auth/google/start`, and open its returned `authorization_url` in
   the **same browser**. Consent completes against the matching nonce cookie.
   Check `/gmail/accounts` for the verified account ID/address.

5. Before the first sync, explicitly attest that this verified mailbox owns the
   old inbox, then link it (replace the placeholder with the verified account ID):

   ```powershell
   .\env\Scripts\python.exe backend_admin.py claim-legacy --account-id <verified-account-id> --confirm-ownership
   ```

   The operator command preserves email IDs and children and rejects duplicate
   message conflicts. It cannot prove mailbox identity for you. Do not run it if
   ownership is uncertain. Quarantined data remains invisible to regular users.

6. Call `POST /gmail/accounts/{id}/sync` with the bearer token. Repeat once to
   verify history-based incremental sync. Inspect status and counts. No message
   sending or Gmail modification API is used.

Do not run production schema commands from tests. The tests validate a distinct
`_test` database and block production-engine connections. Migration roundtrips run
in a transaction-isolated schema of that database. Test rows roll back after each
test; the test schema itself retains the new migration tables.

### Synchronization, transactions and processing

Bootstrap captures the current Gmail history ID before listing all message pages
(including spam/trash). That starting point ensures changes during listing are
replayed next time. Incremental sync consumes every history page, deduplicates
message IDs and fetches current content/labels. A message GET 404 deletes its local
copy and FK-cascaded children; successful full recovery also removes messages no
longer present. History 404 triggers full recovery. Other errors retain the cursor.
The cursor advances only after all source writes succeed. Successful writes survive
partial fetch failures; replay is safe because of account/message uniqueness.

A PostgreSQL transaction advisory lock per account rejects overlapping syncs with
409. A row lock also serializes credential reconnect/disconnect. Network retries
are bounded (three retries for supported transient API failures, 30-second request
timeouts). Sync is synchronous and may hold a transaction during a large bootstrap;
there is no scheduler, worker or queue. This is appropriate for the current local
size; large-mailbox latency/transaction duration still needs load testing.

Raw Gmail payload, headers, labels and typed timestamps are stored before optional
enrichment. `email_pipeline.py` runs cleaning, classification/priority, summary,
tasks/deadlines, facts and embedding stages using savepoints. Each records hash,
version, status, attempt count and a safe error code. One enrichment failure leaves
the source and independent stages intact. A later sync retries failed stages even
when there are no new history events. Changed inputs/version trigger replacement;
existing pre-checkpoint derived data is adopted initially to preserve legacy work.
Fact/index stages keep their own provenance and content hashes. Bump the relevant
stage version when changing derivation logic. Operator maintenance scripts are
privileged and must not be exposed as HTTP endpoints.

A process crash before transaction commit rolls that sync back; the prior cursor
ensures replay. No distributed transaction can atomically commit Google's token
rotation and PostgreSQL: a DB failure immediately after external token rotation
may require reconnect. Transactions and encrypted refresh persistence cover normal
success and handled provider failures, not that external-system atomicity gap.

Timestamp fields:

- `email_date` / API `date`: original Date header text retained for compatibility.
- `sent_at`: safely parsed, aware Date-header timestamp; never an event/deadline.
- `message_at`: Gmail `internalDate` in epoch milliseconds, stored as timestamptz;
  Gmail ordering timestamp, not a promise of human sent time or an event date.
- `created_at`: local database insertion time.
- `last_synced_at`: completion timestamp of source sync.
- Existing task/fact date-only values and deadline timestamps keep their semantics.

UTC conversion happens on input. PostgreSQL may display equivalent aware values
in the session timezone (locally Asia/Riyadh). No event date is synthesized from a
message timestamp, and RAG grounding/prompt rules were not tuned in this phase.

### API compatibility and remaining deployment work

All data/search/ask/classify/account/start routes require a bearer token. Health and
API documentation are public; callback uses its one-use handshake instead of a
bearer header because Google redirects cannot add that header. Unknown/unowned
email/account IDs return the same 404. Inbox filters, pagination, sorting and
`/ask` payload remain; detail/list add typed timestamps. Email detail also reports safe per-stage processing status/attempt counts so failed
or stale enrichment is visible. Inbox listing excludes both
full body and raw payload from SQL loading. Raw payload/credential fields are never
serialized. GET `/gmail/messages` was intentionally replaced with POST.

The backend auth mechanism is usable for controlled backend clients. Browser
login/SSO, account recovery/MFA, managed secret storage, TLS termination, deployment
rate/concurrency limits, monitoring, retention policy, restore drills and an actual
least-privilege DB role are still deployment/frontend work. A compromised operator
or arbitrary server code can access the privileged maintenance connection; ORM
scoping is not a substitute for DB/host security. The current local DB remains
unmigrated until its ownership is explicitly confirmed and these manual steps are
performed. Live Google reconnection and incremental sync must then be verified.

References: [Gmail synchronization](https://developers.google.com/workspace/gmail/api/guides/sync),
[Gmail message timestamp semantics](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages),
[SQLAlchemy loader criteria](https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html#sqlalchemy.orm.with_loader_criteria),
[Fernet and key rotation](https://cryptography.io/en/latest/fernet/).
