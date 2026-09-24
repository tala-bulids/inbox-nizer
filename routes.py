from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse

from sqlalchemy.orm import Session

from schemas import EmailRequest
from predict import classify_email
from gmail_auth import create_google_flow
from gmail_service import get_gmail_service
from email_utils import extract_email_body
from database import get_db
from models import Email, EmailPrediction
from priority import calculate_priority
from typing import Literal

router = APIRouter()


# ---------------------------------------------------------
# Fetch Gmail messages, classify them, and save to database
# ---------------------------------------------------------

@router.get("/gmail/messages")
def get_messages(db: Session = Depends(get_db)):
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        maxResults=5
    ).execute()

    messages = results.get("messages", [])

    if not messages:
        return {"message": "No emails found"}

    classified_emails = []

    for message in messages:
        message_id = message["id"]

        try:
            email = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            payload = email.get("payload", {})
            headers = payload.get("headers", [])

            subject = next(
                (
                    header["value"]
                    for header in headers
                    if header["name"].lower() == "subject"
                ),
                ""
            )

            sender = next(
                (
                    header["value"]
                    for header in headers
                    if header["name"].lower() == "from"
                ),
                ""
            )

            date = next(
                (
                    header["value"]
                    for header in headers
                    if header["name"].lower() == "date"
                ),
                ""
            )

            cleaned_body = extract_email_body(payload)

            predictions = classify_email(
                subject,
                cleaned_body
            )
            priority = calculate_priority(predictions)

            # Check if Gmail message already exists
            existing_email = (
                db.query(Email)
                .filter(Email.message_id == message_id)
                .first()
            )

            # -------------------------------------------------
            # New email
            # -------------------------------------------------

            if existing_email is None:
                db_email = Email(
                    message_id=message_id,
                    sender=sender,
                    email_date=date,
                    subject=subject,
                    body=cleaned_body,
                    priority_score=priority["priority_score"],
                    priority_level=priority["priority_level"]
                )

                db.add(db_email)

                # Get the new email ID before commit
                db.flush()

                # Save ALL model predictions
                for prediction in predictions:
                    db_prediction = EmailPrediction(
                        email_id=db_email.id,
                        category=prediction["category"],
                        confidence=prediction["confidence"]
                    )

                    db.add(db_prediction)

            # -------------------------------------------------
            # Existing email
            #
            # Old emails were saved before email_predictions
            # existed. If they have no predictions yet,
            # populate them now.
            # -------------------------------------------------

            elif not existing_email.predictions:
                for prediction in predictions:
                    db_prediction = EmailPrediction(
                        email_id=existing_email.id,
                        category=prediction["category"],
                        confidence=prediction["confidence"]
                    )

                    db.add(db_prediction)

            db.commit()

            classified_emails.append({
                "id": message_id,
                "from": sender,
                "date": date,
                "subject": subject,
                "body": cleaned_body,
                "predictions": predictions
            })

        except Exception:
            db.rollback()

            classified_emails.append({
                "id": message_id,
                "error": "Failed to process email"
            })

    success_count = sum(
        1
        for email in classified_emails
        if "error" not in email
    )

    failed_count = sum(
        1
        for email in classified_emails
        if "error" in email
    )

    return {
        "count": len(classified_emails),
        "success_count": success_count,
        "failed_count": failed_count,
        "emails": classified_emails
    }


# ---------------------------------------------------------
# Read saved emails from PostgreSQL
# Optional filter by category
# ---------------------------------------------------------

@router.get("/emails")
def get_saved_emails(
    category: str | None = None,
    priority_level: Literal["low", "medium", "high"] | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Email)
    
    if category:
        query = query.filter(
            Email.predictions.any(
                EmailPrediction.category == category
            )
        )

    if priority_level:
        query = query.filter(
            Email.priority_level == priority_level
        )

    emails = (
        query
        .order_by(Email.id.desc())
        .all()
    )

    return {
        "count": len(emails),
        "emails": [
            {
                "id": email.id,
                "message_id": email.message_id,
                "from": email.sender,
                "date": email.email_date,
                "subject": email.subject,
                "body": email.body,
                "priority_score": email.priority_score,
                "priority_level": email.priority_level,
                "predictions": [
                    {
                        "category": prediction.category,
                        "confidence": prediction.confidence
                    }
                    for prediction in email.predictions
                ],
                "created_at": email.created_at
            }
            for email in emails
        ]
    }


# ---------------------------------------------------------
# Google OAuth Login
# ---------------------------------------------------------

@router.get("/auth/google")
def google_login():
    flow = create_google_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    response = RedirectResponse(
        authorization_url
    )

    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True
    )

    response.set_cookie(
        key="oauth_code_verifier",
        value=flow.code_verifier,
        httponly=True,
        samesite="lax",
        max_age=600
    )

    return response


# ---------------------------------------------------------
# Google OAuth Callback
# ---------------------------------------------------------

@router.get("/auth/google/callback")
def google_callback(
    code: str,
    state: str,
    request: Request
):
    saved_state = request.cookies.get(
        "oauth_state"
    )

    if state != saved_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state"
        )

    code_verifier = request.cookies.get(
        "oauth_code_verifier"
    )

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail="OAuth session expired. Start Google login again."
        )

    flow = create_google_flow(
        state=state,
        code_verifier=code_verifier
    )

    flow.fetch_token(code=code)

    credentials = flow.credentials

    with open("token.json", "w") as token:
        token.write(
            credentials.to_json()
        )

    response = JSONResponse({
        "message": "Google account connected successfully"
    })

    response.delete_cookie(
        "oauth_state"
    )

    response.delete_cookie(
        "oauth_code_verifier"
    )

    return response


# ---------------------------------------------------------
# Manual Email Classification
# ---------------------------------------------------------

@router.post("/classify-email")
def classify(request: EmailRequest):
    try:
        result = classify_email(
            request.subject,
            request.body
        )

        return {
            "predictions": result
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Email classification failed"
        )