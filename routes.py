from fastapi import APIRouter, HTTPException, Request, Depends, Query

from sqlalchemy.orm import Session, defer, selectinload
from sqlalchemy import or_, func

from schemas import EmailRequest
from predict import classify_email
from email_serialization import serialize_email
from database import get_db
from models import Email, EmailPrediction, EmailTask
from typing import Literal
import logging
from semantic_search import semantic_search, SemanticQueryError
from embedding_service import EmbeddingInputError
from rag_api import router as rag_router
from account_routes import router as account_router
from authentication import current_user
from backend_models import ProcessingState
from runtime_capabilities import require_retrieval

router = APIRouter()
router.include_router(rag_router)
router.include_router(account_router)
logger = logging.getLogger(__name__)


@router.get('/search/semantic')
def search_semantic_emails(
    q: str = Query(min_length=1, max_length=4000),
    limit: int = Query(default=10, ge=1, le=50),
    min_score: float | None = Query(default=None, ge=-1, le=1, allow_inf_nan=False),
    db: Session = Depends(get_db),
):
    require_retrieval()
    if not q.strip():
        raise HTTPException(status_code=422, detail='Query must not be empty')
    try:
        matches = semantic_search(db, q, limit, min_score)
    except (SemanticQueryError, EmbeddingInputError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.warning('Semantic search unavailable (%s)', type(error).__name__)
        raise HTTPException(status_code=503, detail='Semantic search is temporarily unavailable') from error
    from email_display_order import newest_first
    matches = newest_first(matches)
    return {'query': q.strip(), 'count': len(matches), 'results': [
        {'email': {'id': item['email'].id, 'from': item['email'].sender,
                   'subject': item['email'].subject, 'summary': item['email'].summary,
                   'date': item['email'].email_date, 'sent_at': item['email'].sent_at,
                   'message_at': item['email'].message_at,
                   'priority_score': item['email'].priority_score,
                   'priority_level': item['email'].priority_level},
         'score': item['score'], 'matched_text': item['matched_text']}
        for item in matches
    ]}


@router.get('/email-categories', response_model=list[str])
def email_categories(principal=Depends(current_user)):
    from classifier_contract import LABELS
    return sorted(LABELS)


@router.get("/emails")
def get_saved_emails(
    category: str | None = None,
    categories: list[str] | None = Query(default=None),
    priority_level: Literal["low", "medium", "high"] | None = None,
    has_tasks: bool | None = None,
    has_deadline: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal['message_date', 'created_at', 'priority_score', 'id'] = 'message_date',
    sort_order: Literal['asc', 'desc'] = 'desc',
    db: Session = Depends(get_db)
):
    query = db.query(Email)
    
    selected_categories = categories or ([category] if category else [])
    if selected_categories:
        query = query.filter(
            Email.predictions.any(
                EmailPrediction.category.in_(selected_categories)
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
    # Parsed sent date, then Gmail internal date. Unknown dates stay last;
    # import time is available only through the explicit legacy sort option.
    sort_columns = {'message_date': func.coalesce(Email.sent_at, Email.message_at),
                    'created_at': Email.created_at, 'priority_score': Email.priority_score, 'id': Email.id}
    column = sort_columns[sort_by]
    ordering = column.asc() if sort_order == 'asc' else column.desc()
    # Keep ties stable and unknown priorities last in either direction.
    tie_breaker = Email.id.asc() if sort_order == 'asc' else Email.id.desc()
    emails = (
        query
        .options(defer(Email.body, raiseload=True), defer(Email.raw_payload, raiseload=True),
                 selectinload(Email.predictions), selectinload(Email.tasks))
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
    result = serialize_email(email, include_body=True)
    result['processing'] = [dict(stage=s.stage, status=s.status, error_code=s.error_code,
                                 attempts=s.attempts, updated_at=s.updated_at)
                            for s in db.query(ProcessingState).filter(ProcessingState.email_id == email.id)
                            .order_by(ProcessingState.stage)]
    return result


@router.post("/classify-email")
def classify(request: EmailRequest, principal=Depends(current_user)):
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
