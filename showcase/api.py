"""Separate ASGI app: curated corpus + local inference, no Gmail or database."""
from threading import Lock
from collections import deque
import time
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from showcase.engine import Engine, collection, lab, tasks
from showcase.intelligence import metadata
from showcase.portfolio import SelectedClassifier, evidence, ROOT
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
    # Public CPU showcase is extractive. Optional GGUF code remains available to
    # explicit offline callers, but cannot be requested through this API.
    mode: Literal['grounded'] = 'grounded'

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


class InferenceBudget:
    """Process-wide rolling budget; stores timestamps only, never IPs or text."""
    def __init__(self, limit=30, window=60, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self.requests=deque()
        self.lock=Lock()

    def admit(self):
        with self.lock:
            now=self.clock()
            while self.requests and self.requests[0]<=now-self.window:
                self.requests.popleft()
            if len(self.requests)>=self.limit:
                return max(1,int(self.requests[0]+self.window-now)+1)
            self.requests.append(now)
            return 0


def create_api(engine=None, predictor=None, budget=None):
    app = FastAPI(title='Inbox-nizer AI Showcase', docs_url=None, redoc_url=None)
    app.add_middleware(BodyLimit)
    engine = engine or Engine()
    inference = Lock()
    predictor = predictor or SelectedClassifier()
    budget = budget or InferenceBudget()

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
        retry=budget.admit()
        if retry:
            raise HTTPException(429, {'code':'rate_limited'}, headers={'Retry-After':str(retry)})
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
        return {'provenance': 'Authored fictional bilingual corpus; not representative mailbox data',
                'metadata': metadata(), 'emails': collection()}

    @app.get('/showcase/lab')
    def experiments():
        return lab()

    @app.get('/showcase/portfolio')
    def portfolio():
        return evidence()

    @app.get('/showcase/reproduction', response_class=PlainTextResponse)
    def reproduction():
        return (ROOT/'docs/phase2/README.md').read_text(encoding='utf-8')

    @app.get('/showcase/tasks')
    def collection_tasks():
        return {'tasks':[task for email in collection() for task in tasks(email)],
                'method':'deterministic source extraction; completion is unknown'}

    @app.get('/showcase/emails/{email_id}/tasks')
    def extract(email_id: int):
        email = next((e for e in collection() if e['id'] == email_id), None)
        if email is None:
            raise HTTPException(404, 'Unknown collection email')
        return {'tasks': tasks(email), 'method': 'rule-based extraction; confidence is rule strength'}

    @app.post('/showcase/analyze')
    def analyze(request: Analyze):
        return compute(lambda: engine.analyze(request.subject, request.body))

    @app.post('/showcase/predict')
    def selected_prediction(request: Analyze):
        return compute(lambda: predictor.predict(request.subject, request.body))

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
