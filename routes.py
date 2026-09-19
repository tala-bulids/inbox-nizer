from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse

from schemas import EmailRequest
from predict import classify_email
from gmail_auth import create_google_flow
from gmail_service import get_gmail_service
from email_utils import extract_email_body


router = APIRouter()


@router.get("/gmail/messages")
def get_messages():
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

            classified_emails.append({
                "id": message_id,
                "from": sender,
                "date": date,
                "subject": subject,
                "body": cleaned_body,
                "predictions": predictions
            })

        except Exception:
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