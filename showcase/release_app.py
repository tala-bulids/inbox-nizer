"""Reviewed release factory; no migrations, production credentials or fallback models.

This retains the measured full E5 runtime. It is NOT qualified for Render Free.
The separately measured ONNX adapter is intentionally an offline probe only.
"""
import os
import json
import hashlib
from pathlib import Path


def reject_private_configuration():
    # Check names only. Never echo a secret, load .env, or contact its service.
    forbidden = ('DATABASE', 'POSTGRES', 'PGPASSWORD', 'GOOGLE', 'GMAIL', 'OAUTH')
    if any(any(marker in key.upper() for marker in forbidden) for key in os.environ):
        raise RuntimeError('Remove private mailbox configuration before starting the showcase')


def application():
    reject_private_configuration()
    from showcase.api import create_api
    from showcase.engine import Engine
    from showcase.portfolio import SelectedClassifier
    from deploy.render_app import create_app

    dist = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
    if not (dist / 'showcase-build.json').is_file():
        raise RuntimeError('Build the AI showcase frontend before serving it')
    engine, predictor = Engine(), SelectedClassifier()
    try:
        from huggingface_hub import snapshot_download
        manifest = json.loads((dist.parents[1] / 'docs/phase2/evidence/encoder-artifact-manifest.json').read_text(encoding='utf-8'))
        snapshot = Path(snapshot_download(manifest['model'], revision=manifest['revision'], local_files_only=True))
        for name, expected in manifest['local_files_sha256'].items():
            with (snapshot / name.replace('\\', '/')).open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    raise ValueError('Encoder artifact identity mismatch')
        os.environ['EMBEDDING_REVISION'] = manifest['revision']
        # Startup fails closed before accepting traffic. The only inputs are
        # authored public examples. Models/index remain in this single process.
        engine.retrieve('What is the Atlas workshop date?')
        predictor.predict('Fictional interview', 'Thank you for applying. Please confirm your interview.')
    except Exception:
        raise RuntimeError('Showcase model initialization failed; verify approved local artifacts') from None
    api = create_api(engine, predictor, allow_historical=False)

    @api.get('/health/ready')
    def ready():
        return {'status': 'ready', 'mode': 'ai-showcase',
                'classifier': 'phase2-A', 'retrieval': 'multilingual-e5-small',
                'answering': 'extractive'}

    return create_app(api, dist)
