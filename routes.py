from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.responses import RedirectResponse, JSONResponse

from sqlalchemy.orm import Session, defer, selectinload
from sqlalchemy import or_, func

from schemas import EmailRequest
from predict import classify_email
from gmail_auth import create_google_flow
from gmail_service import get_gmail_service
from email_utils import extract_email_body
from email_serialization import serialize_email
from database import get_db
from models import Email, EmailPrediction, EmailTask
from task_extractor import extract_action_items, _same_task
from deadline_extractor import parse_email_datetime
from summarizer import summarize_email
from priority import calculate_priority
from typing import Literal
import logging
from semantic_index import index_email
from semantic_search import semantic_search, SemanticQueryError
from embedding_service import EmbeddingInputError

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Fetch Gmail messages, classify them, and save to database
# ---------------------------------------------------------

@router.get("/gmail/messages")
def get_messages(db: Session = Depends(get_db)):
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        maxResults=60
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
                    summary=summarize_email(subject, cleaned_body),
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

                    existing_email.predictions.append(db_prediction)

            if existing_email is not None and not existing_email.summary:
                existing_email.summary = summarize_email(subject, cleaned_body)

            saved_email = existing_email if existing_email is not None else db_email
            if not saved_email.tasks:
                for task in extract_action_items(subject, cleaned_body, parse_email_datetime(date)):
                    saved_email.tasks.append(EmailTask(**task))
            elif any(task.deadline_confidence is None for task in saved_email.tasks):
                items = extract_action_items(subject, cleaned_body, parse_email_datetime(date))
                for task in saved_email.tasks:
                    matches = [item for item in items if _same_task(task.task, item['task'])]
                    # Ambiguous matches need a deliberate rebuild, not a guessed date.
                    if len(matches) == 1:
                        if any(getattr(task, field) is not None and matches[0][field] is not None
                               and getattr(task, field) != matches[0][field]
                               for field in ('deadline_text', 'deadline_date', 'deadline_at')):
                            continue
                        for field in ('deadline_text', 'deadline_date', 'deadline_at', 'deadline_confidence'):
                            if getattr(task, field) is None:
                                setattr(task, field, matches[0][field])

            saved_id = saved_email.id
            db.commit()
            # Email ingestion is durable even if the embedding model is unavailable.
            try:
                index_email(saved_email, db)
                db.commit()
            except Exception as error:
                db.rollback()
                logger.warning('Semantic indexing failed for email %s (%s); retry sync or backfill',
                               saved_id, type(error).__name__)

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

@router.get('/search/semantic')
def search_semantic_emails(
    q: str = Query(min_length=1, max_length=4000),
    limit: int = Query(default=10, ge=1, le=50),
    min_score: float | None = Query(default=None, ge=-1, le=1, allow_inf_nan=False),
    db: Session = Depends(get_db),
):
    if not q.strip():
        raise HTTPException(status_code=422, detail='Query must not be empty')
    try:
        matches = semantic_search(db, q, limit, min_score)
    except (SemanticQueryError, EmbeddingInputError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.warning('Semantic search unavailable (%s)', type(error).__name__)
        raise HTTPException(status_code=503, detail='Semantic search is temporarily unavailable') from error
    return {'query': q.strip(), 'count': len(matches), 'results': [
        {'email': {'id': item['email'].id, 'from': item['email'].sender,
                   'subject': item['email'].subject, 'summary': item['email'].summary,
                   'priority_score': item['email'].priority_score,
                   'priority_level': item['email'].priority_level},
         'score': item['score'], 'matched_text': item['matched_text']}
        for item in matches
    ]}


@router.get("/emails")
def get_saved_emails(
    category: str | None = None,
    priority_level: Literal["low", "medium", "high"] | None = None,
    has_tasks: bool | None = None,
    has_deadline: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal['created_at', 'priority_score', 'id'] = 'created_at',
    sort_order: Literal['asc', 'desc'] = 'desc',
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

    if has_tasks is not None:
        query = query.filter(Email.tasks.any() if has_tasks else ~Email.tasks.any())

    if has_deadline is not None:
        deadline_exists = Email.tasks.any(or_(
            EmailTask.deadline_text != '',
            EmailTask.deadline_date.is_not(None),
            EmailTask.deadline_at.is_not(None),
        ))
        query = query.filter(deadline_exists if has_deadline else ~deadline_exists)

    total = query.with_entities(func.count(Email.id)).scalar()
    sort_columns = {'created_at': Email.created_at, 'priority_score': Email.priority_score, 'id': Email.id}
    column = sort_columns[sort_by]
    ordering = column.asc() if sort_order == 'asc' else column.desc()
    # Keep ties stable and unknown priorities last in either direction.
    tie_breaker = Email.id.asc() if sort_order == 'asc' else Email.id.desc()
    emails = (
        query
        .options(defer(Email.body, raiseload=True), selectinload(Email.predictions), selectinload(Email.tasks))
        .order_by(ordering.nulls_last(), tie_breaker)
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "count": len(emails),
        "total": total,
        "limit": limit,
        "offset": offset,
        "emails": [serialize_email(email) for email in emails],
    }


@router.get('/emails/{email_id}')
def get_email_detail(email_id: int, db: Session = Depends(get_db)):
    email = (db.query(Email)
             .options(selectinload(Email.predictions), selectinload(Email.tasks))
             .filter(Email.id == email_id)
             .first())
    if email is None:
        raise HTTPException(status_code=404, detail='Email not found')
    return serialize_email(email, include_body=True)


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
