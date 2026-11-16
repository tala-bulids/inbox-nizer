# Current AI showcase guide

[Project README](../README.md) · [Documentation index](README.md) · [Live demo](https://inbox-nizer-beta.onrender.com)

This guide describes the deployed showcase at application commit [3ea9d60](https://github.com/tala-bulids/inbox-nizer/commit/3ea9d607cebffe9e3e8cbbc80097caa6e9518600). Later portfolio documentation commits do not imply another deployment.

## What runs

- React/TypeScript in showcase mode, with Arabic and English interfaces.
- A single FastAPI/Uvicorn process serving the built frontend and the API under `/api`.
- Selected phase-2 A classifier: word/character TF-IDF and Logistic Regression.
- Pretrained multilingual E5: INT8 ONNX question encoder and prepared FP32 corpus embeddings.
- Extractive, source-linked answers and rule-based task/deadline extraction.
- A fixed collection of 24 fictional messages. No personal mailbox or database is needed.

The serving factory is `showcase.free_app:application`. It verifies artifact identities and performs real warm-up inference before readiness. It rejects private Gmail/database configuration rather than loading the historical application. No migration command is part of showcase startup.

## Local setup

Run commands from the repository root unless stated otherwise. Use Python 3.11 (deployment used 3.11.9) and Node 24; the frontend requires Node 22.12 or newer.

### 1. Install and build

```bash
git clone --branch codex/ai-showcase-phase1 https://github.com/tala-bulids/inbox-nizer.git
cd inbox-nizer
python -m venv .venv
```

Activate the environment:

```bash
# Linux/macOS
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Then:

```bash
python -m pip install -r deploy/requirements-showcase-free.txt
npm --prefix frontend ci
npm --prefix frontend run build:showcase
```

Use the minimal requirements above for this runtime. The root research requirements and the default frontend build serve other, historical development paths.

### 2. Provision the exact model assets

A public clone is sufficient for reviewing the code, evidence and frontend tests. **Real local inference requires three private assets; it is not a turnkey public model download.** There is no placeholder inference or automatic replacement model.

| File | Purpose |
| --- | --- |
| `candidate.joblib` | Fitted selected classifier and feature pipeline |
| `model_int8.onnx` | Reviewed E5 query encoder |
| `sentencepiece.bpe.model` | Corresponding tokenizer |

The identities are pinned in [the classifier comparison](phase2/evidence/experiment-comparison.json) and [the Free runtime manifest](../showcase/free-manifest.json). The authored collection and prepared corpus index are included in Git.

Authorized collaborators can use the private [showcase-research-v1 release](https://github.com/tala-bulids/inbox-nizer-model-artifacts/releases/tag/showcase-research-v1). A fine-grained GitHub token must be restricted to that artifact repository with **Contents: read-only** access and an expiry. Do not use a Render credential or commit a token.

This command prompts without echoing the token, supplies it only to the downloader subprocess and does not write it to a configuration file or command history:

```bash
python -c "import getpass, os, subprocess, sys; env=dict(os.environ, SHOWCASE_GITHUB_TOKEN=getpass.getpass('GitHub token (hidden): ')); subprocess.run([sys.executable, '-m', 'showcase.github_artifacts', '--output', 'local_models/showcase-free'], env=env, check=True)"
```

Alternatively, an authorized operator can place the exact three approved files in `local_models/showcase-free/`. The downloader and runtime verify file sizes and SHA-256 digests. Downloads authenticate to GitHub's API; allowed signed asset redirects receive no authorization header. A mismatched existing file is rejected, not silently overwritten. The local model directory is ignored by Git.

Without artifact access, use the public demo and the saved aggregate evidence. Training or downloading a different checkpoint does not reproduce this deployed candidate.

### 3. Select the runtime and launch

Use a terminal without inherited Gmail, Google OAuth or database environment variables. Do not load the historical application's `.env` or `credentials.json`; they are not showcase prerequisites. This is a separate local process and does not require changing any existing credentials.

Linux:

```bash
export SHOWCASE_RUNTIME=e5-int8-fp32-corpus-v1
export SHOWCASE_EMBEDDING_DIR=local_models/showcase-free
export SHOWCASE_CLASSIFIER_PATH=local_models/showcase-free/candidate.joblib
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
sh deploy/with-showcase-memory.sh python -m uvicorn showcase.free_app:application --factory --host 127.0.0.1 --port 4182 --workers 1 --no-access-log
```

Windows PowerShell:

```powershell
$env:SHOWCASE_RUNTIME = "e5-int8-fp32-corpus-v1"
$env:SHOWCASE_EMBEDDING_DIR = "local_models/showcase-free"
$env:SHOWCASE_CLASSIFIER_PATH = "local_models/showcase-free/candidate.joblib"
$env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
python -m uvicorn showcase.free_app:application --factory --host 127.0.0.1 --port 4182 --workers 1 --no-access-log
```

Open [localhost:4182](http://127.0.0.1:4182). Readiness is at [localhost:4182/api/health/ready](http://127.0.0.1:4182/api/health/ready). It reports `ready` and runtime `e5-int8-fp32-corpus-v1` after initialization. Use Ctrl+C to stop.

The allocator launcher is specific to the qualified Linux/glibc environment. Windows or macOS behavior does not reproduce the Linux memory qualification. No local memory rerun is necessary just to explore the interface.

### Frontend-only checks

After installing frontend dependencies:

```bash
cd frontend
npm test -- src/test/showcase.test.tsx
npm run build:showcase
```

Component tests use explicit fixtures. They do not establish real model or hosted acceptance. Existing real-model evidence is linked below.

## Evidence and boundaries

- [Classification preparation, split and model comparison](phase2/README.md): validation informed model selection; no independent test result is claimed.
- [Retrieval and task evaluation](phase3/README.md): small, authored fixtures, distinct from classifier data.
- [Final Linux qualification](free-qualification/MEMORY_OPTIMIZATION.md#final-measured-verdict--pass): 333.140625 MiB cgroup peak, 33.372916% below the 500.0078125 MiB baseline, within a 512 MiB limit and a 400 MiB engineering target.
- [Live frontend acceptance](showcase-portfolio/live-verification.json): recorded on 16 November 2026, Arabic/English at 1440 and 390 px, with real inference and citations.
- [Screenshots](showcase-portfolio/README.md): selected original captures of that deployed frontend.

The Free host can sleep when idle. The memory result is a constrained Linux measurement, not continuous Render telemetry. Neither deployment nor these checks establish production readiness for personal-mail automation.

## Historical implementation

The original Gmail/OAuth/PostgreSQL application, DistilBERT experiments, development reports and branches are retained. Older deployment recipes describe that earlier application and must not be mixed with the showcase startup. Follow the [documentation index](README.md) to read those records in context.
