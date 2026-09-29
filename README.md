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
