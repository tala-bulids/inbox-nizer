# inbox-nizer

An email organization project built with Python, FastAPI, PostgreSQL and a bilingual
Arabic/English React interface. It started with DistilBERT fine-tuning and now includes
read-only Gmail synchronization, classification, summaries, tasks, semantic search
and questions grounded in the user's stored emails.

This is a cooperative-training portfolio project. Representative mailbox accuracy and
a verified public deployment remain outstanding. No model performance claim is made
here. See [validation and limitations](docs/VALIDATION.md).

## Implemented features

- **Classification:** ten-label DistilBERT training with weighted binary cross-entropy.
  The product returns the highest-scoring label and its raw sigmoid score. That score
  is not a calibrated probability of correctness.
- **Inbox:** account-owned Gmail sync, filters, pagination, priority, clean message text,
  summaries, and conservative task/deadline extraction.
- **Search and Ask:** local multilingual embeddings with pgvector, structured facts,
  literal extraction, clarification and optional local GGUF synthesis. Generated
  answers retain an unverified-synthesis notice and source links.
- **Authentication:** Google application sign-in, separate Gmail read consent, encrypted
  OAuth credentials, browser sessions with CSRF checks and operator bearer tokens.
- **Frontend:** Inbox, Email Detail, Search, Ask Mail, Tasks and Settings, with the
  existing retro design and Arabic/English presentation.

Categories: Business, Customer Support, Events & Invitations, Finance & Bills,
Job Application, Newsletters, Personal, Promotions, Reminders, Travel & Bookings.

## Classifier quick start

Python 3.11 is the validated interpreter. No database, Gmail credentials or web server
is required for training, command-line prediction or evaluation.

```powershell
git clone https://github.com/tala-bulids/inbox-nizer.git inbox-nizer
cd inbox-nizer
python -m venv env
.\env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux/macOS activate with `source env/bin/activate`. Direct Python dependencies
are pinned to the tested environment; optional GGUF support is separate. CPU is supported.
For CUDA-specific PyTorch packages, follow PyTorch's instructions for your hardware.

### Data and base model

Training accepts a local `.arrow` file, JSON list, or JSONL rows with `subject`, `body`
and a nonempty `labels` list. An already prepared `text` field is also supported.
A row looks like this; a single row is not enough to train:

```json
{"subject":"Interview invitation","body":"Please confirm your attendance.","labels":["Job Application"]}
```

Use sufficient independent examples to populate every training class. Contradictory
exact duplicates are quarantined. Template/near-duplicate groups and available sender
domains stay within one partition. Unsplittable datasets are rejected.

The original project used `imnim/multiclass-email-classification`. Download public data
and the base model explicitly when online, or provide your own authorized local data:

```powershell
hf download distilbert-base-uncased --local-dir results/distilbert-base
python -c "from pathlib import Path; from datasets import load_dataset; Path('results').mkdir(exist_ok=True); load_dataset('imnim/multiclass-email-classification', split='train').to_json('results/training.jsonl')"
```

Public annotations are not representative human-reviewed mailbox gold. The English
base model does not establish Arabic classification quality. Keep private data outside
Git; `results/` is ignored. Training and inference read local artifacts only.

### Training, prediction and evaluation

```powershell
python app.py --dataset-file results/training.jsonl --base-model results/distilbert-base --epochs 3
python predict.py --subject "Interview invitation" --body "Please confirm your attendance."
python evaluate.py --samples examples/evaluation.json --output results/evaluation.json
```

All three commands default to **`results/email-classifier`**, resolved against the
project directory. `EMAIL_MODEL_PATH` in the environment or project `.env` overrides
that shared location. `--output-dir` (training) and `--model` (prediction/evaluation)
override it for one command. Explicit relative artifact paths are also project-relative;
data/sample paths are relative to the shell's working directory.

Training refuses nonempty output directories. Evaluate a new candidate explicitly
before changing `EMAIL_MODEL_PATH`. Existing `results/checkpoint-3159` installations
remain usable by setting that path explicitly. No legacy weights are moved or replaced.

Artifacts contain weights, tokenizer, label mappings, multi-label problem type, training
token limit, split manifest and training report. Prediction and evaluation share loading,
preprocessing, truncation and sigmoid scoring. Missing/incompatible artifacts fail
instead of downloading a substitute model. Model weights are not included in Git.

Validation macro F1 and top-one accuracy select the checkpoint, with early stopping.
The test partition is untouched unless `--evaluate-test` is explicitly requested for a
final diagnostic. Never repeatedly use test results to select candidates. The example
evaluation file is synthetic and is not an accuracy benchmark.

References: [DistilBERT](https://huggingface.co/docs/transformers/model_doc/distilbert)
and [model saving/loading](https://huggingface.co/docs/transformers/main_classes/model).

## Full application setup

1. Install PostgreSQL with pgvector available. Provision an application database and a
   separate database ending in `_test`. Production needs distinct migration and
   restricted runtime roles.
2. Copy `.env.example` to `.env` and replace database placeholders. Generate a key with
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   and store it locally as `OAUTH_TOKEN_KEYS`.
3. For a **new empty development database**, run `python -m alembic upgrade head`.
   For an existing mailbox, first follow [backup, quarantine and ownership procedures](deploy/OPERATIONS.md).
   Maintenance/backfill scripts are not ordinary startup steps.
4. Configure a Google web OAuth client, save its JSON as `credentials.json` and register
   both callbacks from `.env.example`. Invite your verified address through
   `GOOGLE_LOGIN_ALLOWED_EMAILS`. Application login and Gmail consent are separate.
   Testing-mode OAuth apps also require an allowed Google Console test user.
5. Start the backend:

   ```powershell
   python -m uvicorn main:app --host localhost --port 8000 --no-access-log
   ```

6. In another terminal, run the frontend (Node 24+ recommended for browser checks):

   ```powershell
   cd frontend
   npm ci
   Copy-Item .env.example .env
   npm run dev
   ```

Open `http://localhost:5173`, sign in, connect Gmail in Settings and explicitly start
sync. Use `localhost` consistently for local cookies and callbacks. Swagger is at
`http://localhost:8000/docs`. Operator clients can provision a bearer token with
`python backend_admin.py create-user --name local-owner`.

Semantic search requires a locally cached `intfloat/multilingual-e5-small`; prepare it
with `hf download intfloat/multilingual-e5-small`. See [model setup](docs/MODELS.md) for
optional GGUF generation. Failed enrichment is recorded per message and can be retried.

More: [frontend](frontend/README.md), [deployment](deploy/README.md),
[bounded sync](deploy/BOUNDED_SYNC.md), [Google release requirements](deploy/GOOGLE_PUBLIC_RELEASE.md).
Real consent, hosted TLS, restore drills and production capacity need separate validation.

## Tests and checks

Offline classifier mechanics tests need no database or downloaded model:

```powershell
python -m pytest tests/unit --confcutdir=tests/unit -q
```

For the full suite, configure `DATABASE_URL` and a distinct `TEST_DATABASE_URL` ending
in `_test`, with pgvector available:

```powershell
python -m pytest -q
python -m unittest quality.test_local_classifier_review -v
python -m pip check
```

The full suite blocks production-engine connections and rolls back fixture rows.
A fresh test database is initialized through the migration chain. Real provider/model
benchmarks are opt-in. The classifier roundtrip uses tiny random weights and synthetic
data: it verifies pipeline mechanics, not prediction quality.

From `frontend/`:

```powershell
npm run api:generate
npm run typecheck
npm run lint
npm test
npm run build
```

GitHub Actions runs the backend with PostgreSQL/pgvector and the frontend checks.

## Project structure

```text
inbox-nizer/
  app.py, predict.py, evaluate.py       # Training, prediction and evaluation CLIs
  classifier_config.py                 # Shared artifact paths
  classifier_contract.py               # Labels, problem type and token limits
  main.py, routes.py, schemas.py        # FastAPI application and API
  authentication.py, browser_auth.py   # Bearer/session authentication
  google_login.py, gmail_*.py          # Sign-in, consent and bounded sync
  email_*.py, task_*.py, priority.py   # Cleaning and enrichment
  rag_*.py, fact_*.py, semantic_*.py   # Grounded answers and retrieval
  alembic/                             # Preserved migration history
  frontend/                            # React/TypeScript UI and tests
  quality/                             # Diagnostics and private review tools
  tests/unit/, test_*.py               # Classifier and integration tests
  examples/                            # Synthetic sample inputs
  deploy/, docs/                       # Current guides and historical notes
  results/, private_review/            # Local artifacts; ignored by Git
```

All 24 accessible local development commits are preserved above the original GitHub
commit, together with the reviewed accessible working-tree source. See
[source provenance](docs/SOURCE_AUDIT.md). Historical reports live in `docs/history/`;
their metrics are not new results or current production claims.
