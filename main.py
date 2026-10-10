from fastapi import FastAPI
from routes import router
from task_api import router as task_router
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from ownership import OwnershipError
from backend_config import ConfigurationError
from privacy_middleware import PrivateQueryMiddleware

app = FastAPI()
app.add_middleware(PrivateQueryMiddleware)

app.include_router(router)
app.include_router(task_router)


@app.exception_handler(SQLAlchemyError)
@app.exception_handler(OwnershipError)
@app.exception_handler(ConfigurationError)
async def backend_unavailable(request, error):
    return JSONResponse(status_code=503, content={'detail': 'Backend temporarily unavailable'})


@app.get("/")
def root():
    return {"message": "AI Smart Inbox API is running"}
