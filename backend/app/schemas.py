from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field, StringConstraints

from .ai_summary.schema import CandidateSummary
from .models import Stage

MAX_RESUME_CHARS = 50_000


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: Optional[str] = Field(default=None, max_length=50)
    role: str = Field(min_length=1, max_length=200)
    resume_text: str = Field(default="", max_length=MAX_RESUME_CHARS)
    stage: Stage = Stage.applied
    source: Optional[str] = Field(default=None, max_length=100)


class NoteCreate(BaseModel):
    # Strip before the length check so a whitespace-only note is rejected.
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class StageUpdate(BaseModel):
    stage: Stage


class ArchiveUpdate(BaseModel):
    archived: bool


class NoteOut(BaseModel):
    id: int
    text: str
    created_at: datetime


class CandidateListItem(BaseModel):
    id: int
    name: str
    email: str
    role: str
    stage: Stage
    source: Optional[str]
    archived: bool
    created_at: datetime


class CandidateDetail(CandidateListItem):
    phone: Optional[str]
    resume_text: str
    notes: list[NoteOut]
    summary: Optional[CandidateSummary]
    summary_generated_at: Optional[datetime]
