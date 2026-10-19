# inbox-nizer source provenance

Inspection date: 18 October 2026.

The repository was renamed to `tala-bulids/inbox-nizer` during this update.

## Accessible sources

- GitHub repository: `tala-bulids/email-classification-finetuning` at inspection.
- GitHub branch listing and an authenticated fetch both found only `main` at
  `88d154e1b919eb52b552fc81c5abf48bd8410520` (the initial commit).
- The GitHub pull-request listing was empty, including closed requests. There was
  no remote unmerged branch to incorporate at the time of inspection.
- The provided local workspace had `main` at `90bdda1` and
  `frontend-retro-redesign` at `39046c2`, plus accessible modified/untracked source.
  The latter contains all 24 local commits following the GitHub initial commit.
- The release branch was created from `39046c2` in an isolated checkout. Available
  source files were copied into it, reviewed and fixed. The original local branch,
  uncommitted work and working environment were not reset, stashed or overwritten.

These local commits and working-tree files were accessible during this task; they
were not already on GitHub. No claim is made about changes on another device or in
unavailable directories. This update does not squash or rewrite existing history.

## Incorporated local work

The existing FastAPI/PostgreSQL application, migration chain, Gmail consent and sync,
tenant ownership, browser/Google login, cleaning, classification, summaries, tasks,
semantic retrieval, grounded Ask flow, review tooling and bilingual retro frontend
are preserved. Uncommitted additions include the later auth/sync migrations, bounded
sync, classifier contract/data audits, answer presentation and regression tests.

`desktop.ini` is omitted as OS metadata. The accidental Python-named diff `t_gmail.py`
is preserved as `docs/history/legacy-workspace.patch`. Earlier README content and
local quality reports are archived with explicit historical labels. Historical
metrics are not presented as measurements from this update.

Ignored credentials, `.env`, tokens, database backups, real mailbox exports, model
weights, caches and training outputs are not included. A loose untracked
`email_classifier/config.json` was excluded with its ignored companion weights and
tokenizer so the repository does not advertise an incomplete model artifact.

## Preserved commit chain

- `57c1130` Refactor email prediction into reusable function
- `6032fea` Add FastAPI email classification endpoint
- `3cbaa53` Add API tests
- `bd16467` Add error handling for classification endpoint
- `98f547f` Update README for FastAPI backend
- `a26fe13` Add Google OAuth authentication for Gmail
- `e601927` Fetch and classify Gmail messages
- `70b3936` Fetch and classify multiple Gmail messages
- `a0c5d22` test: add Gmail API coverage and finalize MVP docs
- `dfb835d` feat: add PostgreSQL persistence and multi-label predictions
- `8d902ed` feat: add email priority scoring and isolated test database
- `20fb51c` feat: add email summaries tasks and deadline extraction
- `5e2d46e` feat: add pagination sorting and email detail API
- `0e48019` refactor: improve email content quality and action extraction
- `caf11fd` feat: add pgvector semantic email search
- `66da332` feat: add local grounded RAG for email Q&A
- `31619a5` feat: add structured facts and deterministic hybrid answering
- `dede590` feat: scale RAG retrieval and harden answer reliability
- `c34821c` feat: freeze AI answer contract for frontend
- `16ce15d` feat: add frontend foundation for AI smart inbox
- `cacd3a7` feat: complete inbox and email detail experience
- `2c11ee0` feat: complete ask AI and semantic search experience
- `90bdda1` feat: add tasks API and complete Gmail settings
- `39046c2` feat: redesign frontend with Inbox+nizer retro UI

A final local-source check on 19 October also incorporated the accessible review-tool
process-lock and blocked-browser-storage fixes added during this task. Portable paths
and project naming were retained. No private review CSV was copied.
