"""Private questions belong in a POST body, not a URL."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session
from database import get_db
from embedding_service import EmbeddingInputError
from local_llm import get_llm_provider, ContextTooLarge, ProviderUnavailable
from rag_service import answer_email_question, InvalidGeneration, insufficient_answer

router = APIRouter()


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=2000)
    chunk_limit: int = Field(default=4, ge=1, le=20)
    max_chunks_per_email: int = Field(default=2, ge=1, le=5)
    min_score: float | None = Field(default=None, ge=-1, le=1, allow_inf_nan=False)
    max_context_chars: int = Field(default=6000, ge=1000, le=12000)
    email_id: int | None = Field(default=None, gt=0)
    history: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("history")
    @classmethod
    def bounded_history(cls, values):
        if any(not value.strip() or len(value)>2000 for value in values):
            raise ValueError("Invalid conversation turn")
        return values

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


class ClarificationOption(BaseModel):
    email_id: int
    subject: str
    date: str


class AnswerResponse(BaseModel):
    answer: str
    sources: list[Source]
    citations: list[Citation]
    status: Literal['answered', 'insufficient_evidence', 'needs_clarification']
    clarification_options: list[ClarificationOption] | None = None
    answer_mode: Literal['deterministic_fact', 'extractive', 'generated_synthesis'] | None = None
    verification: Literal['source_supported', 'not_semantically_verified'] | None = None


class _LazyProvider:
    def generate(self, messages):
        return get_llm_provider().generate(messages)


@router.post('/ask', response_model=AnswerResponse, response_model_exclude_none=True)
def ask(request: QuestionRequest, db: Session = Depends(get_db)):
    try:
        return answer_email_question(db, llm=_LazyProvider(), **request.model_dump())
    except EmbeddingInputError as error:
        raise HTTPException(422, str(error)) from None
    except (InvalidGeneration, ContextTooLarge):
        return insufficient_answer(request.question)
    except ProviderUnavailable as error:
        raise HTTPException(503, str(error)) from None
    except Exception:
        # Do not expose provider errors containing private prompts or credentials.
        raise HTTPException(503, 'Inbox question service is temporarily unavailable.') from None
