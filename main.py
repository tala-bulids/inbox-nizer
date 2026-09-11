from fastapi import FastAPI
from pydantic import BaseModel
from predict import classify_email

app = FastAPI()


class EmailRequest(BaseModel):
    subject: str
    body: str


@app.get("/")
def root():
    return {"message": "AI Smart Inbox API is running"}


@app.post("/classify-email")
def classify(request: EmailRequest):
    result = classify_email(request.subject, request.body)

    return {
        "predictions": result
    }