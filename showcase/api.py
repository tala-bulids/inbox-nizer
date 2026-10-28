"""Separate ASGI app: curated corpus + local inference, no Gmail or database."""
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from showcase.engine import Engine, collection, lab, tasks
from embedding_service import EmbeddingInputError


class Analyze(BaseModel):
    model_config = ConfigDict(extra='forbid')
    subject: str = Field(default='', max_length=300)
    body: str = Field(min_length=1, max_length=6000)

    @field_validator('body')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Empty input')
        return value.strip()


class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=1000)
    mode: Literal['grounded', 'synthesis'] = 'grounded'

    @field_validator('question')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Empty question')
        return value.strip()


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > 24000:
                return await JSONResponse({'code': 'input_too_large'}, status_code=413)(scope, receive, send)
            if not message.get('more_body', False):
                break
        delivered = False
        async def replay():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
        await self.app(scope, replay, send)


def create_api(engine=None):
    app = FastAPI(title='Inbox-nizer AI Showcase', docs_url=None, redoc_url=None)
    app.add_middleware(BodyLimit)
    engine = engine or Engine()
    inference = Lock()

    @app.middleware('http')
    async def private_responses(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        # Do not echo submitted text (FastAPI's default validation includes it).
        return JSONResponse({'code': 'invalid_input'}, status_code=422)

    def compute(operation):
        if not inference.acquire(blocking=False):
            raise HTTPException(429, {'code': 'inference_busy'}, headers={'Retry-After': '2'})
        try:
            return operation()
        except EmbeddingInputError:
            raise HTTPException(422, {'code': 'input_too_long'}) from None
        except Exception:
            raise HTTPException(503, {'code': 'model_unavailable'}) from None
        finally:
            inference.release()

    @app.get('/health/live')
    def live():
        return {'status': 'alive', 'mode': 'ai-showcase', 'model_readiness': 'not_checked'}

    @app.get('/showcase/collection')
    def emails():
        return {'provenance': 'Authored fictional bilingual corpus; not evaluation data', 'emails': collection()}

    @app.get('/showcase/lab')
    def experiments():
        return lab()

    @app.get('/showcase/emails/{email_id}/tasks')
    def extract(email_id: int):
        email = next((e for e in collection() if e['id'] == email_id), None)
        if email is None:
            raise HTTPException(404, 'Unknown collection email')
        return {'tasks': tasks(email), 'method': 'rule-based extraction; confidence is rule strength'}

    @app.post('/showcase/analyze')
    def analyze(request: Analyze):
        return compute(lambda: engine.analyze(request.subject, request.body))

    @app.post('/showcase/ask')
    def ask(request: Question):
        return compute(lambda: engine.ask(request.question, request.mode))

    return app


app = create_api()


def application():
    # Reuse same-origin SPA serving and security headers without importing main.
    from pathlib import Path
    from deploy.render_app import create_app
    dist = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
    if not (dist / 'showcase-build.json').is_file():
        raise RuntimeError('Build the AI showcase frontend before serving it')
    return create_app(app, dist)
