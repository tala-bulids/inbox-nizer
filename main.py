from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from routes import router
from task_api import router as task_router
from browser_auth import router as browser_router
from google_login import router as google_login_router
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from ownership import OwnershipError
from backend_config import ConfigurationError
from privacy_middleware import PrivateQueryMiddleware
from deployment_health import router as health_router

app = FastAPI(title='inbox-nizer', description='Email classification and local inbox assistance.')
app.add_middleware(PrivateQueryMiddleware)

app.include_router(router)
app.include_router(task_router)
app.include_router(browser_router)
app.include_router(google_login_router)
app.include_router(health_router)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    # Validation errors include raw rejected inputs by default.
    return JSONResponse(status_code=422, content={'detail': 'Invalid request'})


@app.exception_handler(SQLAlchemyError)
@app.exception_handler(OwnershipError)
@app.exception_handler(ConfigurationError)
async def backend_unavailable(request, error):
    return JSONResponse(status_code=503, content={'detail': 'Backend temporarily unavailable'})


@app.get("/")
def root():
    return {"message": "inbox-nizer API is running"}
