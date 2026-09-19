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
