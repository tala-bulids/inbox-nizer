"""Separately selected Free candidate; the original release factory is preserved."""
import os
from pathlib import Path

from showcase.release_app import reject_private_configuration
from showcase.free_runtime import RUNTIME_ID, components, runtime_info


def application():
    reject_private_configuration()
    if os.environ.get('SHOWCASE_RUNTIME') != RUNTIME_ID:
        raise RuntimeError('Explicit SHOWCASE_RUNTIME selection is required')
    from showcase.api import create_api
    from deploy.render_app import create_app
    dist = Path(__file__).resolve().parents[1]/'frontend/dist'
    if not (dist/'showcase-build.json').is_file():
        raise RuntimeError('Build the showcase frontend before serving')
    try:
        engine, predictor, encoder = components()
        engine.ask('What is the Atlas workshop date?')
        predictor.predict('Fictional interview', 'Please confirm your interview.')
    except Exception:
        raise RuntimeError('Free candidate initialization failed; verify approved artifacts') from None
    app = create_api(engine, predictor, allow_historical=False, runtime=runtime_info())
    # Internal handles for offline qualification; no diagnostic routes are served.
    app.state.engine, app.state.predictor, app.state.encoder = engine, predictor, encoder

    @app.get('/health/ready')
    def ready():
        return {'status': 'ready', 'mode': 'ai-showcase', **runtime_info()}

    return create_app(app, dist)
