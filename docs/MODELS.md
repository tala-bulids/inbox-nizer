# inbox-nizer local model setup

## Email classifier

Follow the root README to train a local artifact or explicitly select an existing
one with `EMAIL_MODEL_PATH`. The default is `results/email-classifier`. The legacy
`results/checkpoint-3159` directory is supported only when explicitly selected.
Git does not distribute trained weights, tokenizers, private datasets or checkpoints.

Artifacts must include model weights, configuration and tokenizer. The ten labels and
their inverse mappings must agree with `classifier_contract.py`, and the problem type
must be `multi_label_classification`. The runtime uses sigmoid and returns only the
best category. Newly trained artifacts persist their training length in both model
configuration and tokenizer metadata. Legacy artifacts fall back to the smaller of
the tokenizer limit, model positions and 512 tokens.

No candidate is automatically promoted based on unit tests. A real release requires
representative human-reviewed evaluation; see `quality/classifier_release.py` and
the private review guides at the repository root. Changing a checkpoint does not
automatically reclassify stored emails.

## Semantic embeddings

The encoder is `intfloat/multilingual-e5-small`, with normalized 384-dimensional
vectors and a 512-token limit. It loads from the local Hugging Face cache only:

```sh
hf download intfloat/multilingual-e5-small
```

PostgreSQL must have pgvector available. The migrations create its extension and
storage schema. Existing backfill and reprocessing commands are privileged operator
tools; review backups, ownership and the deployment runbook before using them.

## Optional local synthesis

`local_llm.py` uses Qwen3-0.6B in GGUF format, lazily, on CPU. The Windows x64 wheel
is pinned separately and is not a portable requirements file:

```powershell
python -m pip install -r requirements-local.txt
python download_rag_model.py
```

The downloader fetches only the repository/revision/file declared in its source and
checks size and SHA-256 before publishing the local file. It refuses to replace an
existing wrong file. The default path is `local_models/Qwen3-0.6B-Q4_K_M.gguf`.
`RAG_MODEL_PATH` can select an existing local file; use an absolute path for deployment.
`RAG_THREADS`, `RAG_CONTEXT_SIZE` and `RAG_MAX_NEW_TOKENS` control the bounded runtime.
There is no automatic download at application startup or during inference.

On other operating systems, install a compatible llama-cpp-python build separately
and validate it on that host. The core test suite substitutes model/provider fixtures;
it does not establish actual synthesis quality, throughput or production capacity.

## Historical experiment scripts

`quality/classification.py`, `classifier_stress.py`, `deeper_classification.py` and
`latency.py` preserve earlier experiments. They require the named legacy candidate
artifacts, public Arrow cache and, for probe comparisons, prior local joblib outputs.
They are not installation or deployment steps. Their older authored FINAL/HOLDOUT
fixtures have already been used during development and are not fresh holdouts.
Use `app.py`, `predict.py` and `evaluate.py` for the supported shared-path pipeline.
