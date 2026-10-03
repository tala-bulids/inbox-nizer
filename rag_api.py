"""Private questions belong in a POST body, not a URL."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session
from database import get_db
from embedding_service import EmbeddingInputError
from local_llm import get_llm_provider, ContextTooLarge, ProviderUnavailable
from rag_service import answer_email_question, InvalidGeneration

router = APIRouter()


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=2000)
    chunk_limit: int = Field(default=4, ge=1, le=20)
    max_chunks_per_email: int = Field(default=2, ge=1, le=5)
    min_score: float | None = Field(default=None, ge=-1, le=1, allow_inf_nan=False)
    max_context_chars: int = Field(default=6000, ge=1000, le=12000)

    @field_validator('question')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Question must not be empty')
        return value.strip()


class Source(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    email_id: int
    chunk_id: int
    chunk_index: int
    score: float
    subject: str
    sender: str = Field(alias='from')
    date: str


class Citation(BaseModel):
    email_id: int


class AnswerResponse(BaseModel):
    answer: str
    sources: list[Source]
    citations: list[Citation]
    status: Literal['answered', 'insufficient_evidence']


@router.post('/ask', response_model=AnswerResponse)
def ask(request: QuestionRequest, db: Session = Depends(get_db)):
    try:
        return answer_email_question(db, llm=get_llm_provider(), **request.model_dump())
    except (ContextTooLarge, EmbeddingInputError) as error:
        raise HTTPException(422, str(error)) from None
    except InvalidGeneration:
        raise HTTPException(502, 'Generated answer failed validation; try a more specific question.') from None
    except ProviderUnavailable as error:
        raise HTTPException(503, str(error)) from None
    except Exception:
        # Do not expose provider errors containing private prompts or credentials.
        raise HTTPException(503, 'Inbox question service is temporarily unavailable.') from None
