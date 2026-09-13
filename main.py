from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from predict import classify_email
from unittest.mock import patch

app = FastAPI()


class EmailRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)

def test_classification_error():
    with patch("main.classify_email", side_effect=Exception("test error")):
        response = client.post(
            "/classify-email",
            json={
                "subject": "Test",
                "body": "Test email"
            }
        )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Email classification failed"
    }
    
@app.get("/")
def root():
    return {"message": "AI Smart Inbox API is running"}


@app.post("/classify-email")
def classify(request: EmailRequest):
    try:
        result = classify_email(request.subject, request.body)

        return {
            "predictions": result
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Email classification failed"
        )