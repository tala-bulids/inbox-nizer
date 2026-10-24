"""Existing Render topology: one process, same-origin SPA and mounted API."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from privacy_middleware import PrivateQueryMiddleware


def create_app(api, dist):
    dist = Path(dist).resolve()
    if not (dist / 'index.html').is_file():
        raise RuntimeError('Build the frontend before starting the hosted service')
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(PrivateQueryMiddleware)

    @app.middleware('http')
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer',
            'X-Frame-Options': 'DENY',
            'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
            'Strict-Transport-Security': 'max-age=31536000',
            'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'",
        })
        return response

    @app.get('/api', include_in_schema=False)
    def api_root():
        return RedirectResponse('/api/')

    app.mount('/api', api)
    app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')

    @app.get('/{path:path}', include_in_schema=False)
    def spa(path: str):
        # Only built public files can be served, including through symlinks.
        candidate = (dist / path).resolve()
        if not candidate.is_relative_to(dist) or any(p.startswith('.') for p in Path(path).parts):
            raise HTTPException(404)
        return FileResponse(candidate if candidate.is_file() else dist / 'index.html')

    return app


def application():
    from main import app as api
    return create_app(api, Path(__file__).resolve().parents[1] / 'frontend' / 'dist')
