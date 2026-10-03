# AI Smart Inbox

AI Smart Inbox is a student portfolio MVP built with FastAPI. It connects to Gmail,
cleans email content, and uses a fine-tuned DistilBERT model to classify messages.

## Features

- Google OAuth login with read-only Gmail access
- Fetch the latest 5 Gmail messages
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

Use Python 3.11. From the project folder, create and activate a virtual environment.
For Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
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
5. Start the app and open `http://localhost:8000/auth/google` in your browser.
6. Complete consent. The callback saves the local `token.json` file.

If the OAuth app is in testing mode, your Google account must be an allowed test user.
Use `localhost` consistently when starting login and returning to the callback.

## Run the app

Run this command from the project folder:

```powershell
fastapi dev main.py
```

API documentation: [Swagger UI](http://localhost:8000/docs).

## Main endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Check that the API is running |
| GET | `/auth/google` | Start Google login |
| GET | `/auth/google/callback` | Complete OAuth and save credentials locally |
| GET | `/gmail/messages` | Fetch and classify up to 5 Gmail messages |
| POST | `/classify-email` | Classify a supplied subject and body |

Example request for `POST /classify-email`:

```json
{
  "subject": "Interview invitation",
  "body": "We would like to invite you for an interview on Monday."
}
```

When messages are found, `GET /gmail/messages` returns `count`, `success_count`,
`failed_count`, and `emails`. Successful entries include `id`, `from`, `date`,
`subject`, `body`, and `predictions`. A failed entry includes its `id` and the
safe message `"Failed to process email"`; remaining messages continue processing.

The current empty-inbox response is:

```json
{"message": "No emails found"}
```

## Run tests

From the project folder:

```powershell
pytest -v
```

Gmail tests mock `routes.get_gmail_service`, extraction, and classification. They
cover success, per-message failures, and empty responses without contacting Gmail.
OAuth tests use synthetic credentials and mock the token exchange and token-file
write. No Google login is required for tests. The existing API tests still load the
local model, so the model files must be available.

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

This is a local development MVP. It uses HTTP on localhost for OAuth and stores a
single account's token locally; it is not a production multi-user authentication system.

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

Gmail commits the email first, then indexes finalized **stored** content in a
separate transaction. Indexing errors are logged without message contents and do
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
inference: too-large requests return 422, without silently truncating evidence.
Try chunk_limit=2 and max_context_chars=2500 for constrained Arabic requests.

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
loading; exact INSUFFICIENT_EVIDENCE also maps to that response. Invalid/empty
answers return 502; context overflow returns 422; sanitized backend failures 503.
No question/source logging, tools, actions, hosted generation, billing or telemetry
are added. Only the manual model download contacts Hugging Face; inbox data never
leaves the machine through this provider. Keep the API bound to localhost within
the project's existing trusted access boundary. This is not multi-user isolation.

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

Gmail ingestion commits the email first, then independently commits fact extraction
and semantic indexing. A fact failure logs only email ID/error class and cannot
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
