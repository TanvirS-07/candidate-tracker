from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Stage(str, Enum):
    applied = "Applied"
    screening = "Screening"
    interview = "Interview"
    offer = "Offer"
    rejected = "Rejected"


class Candidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    phone: Optional[str] = None
    role: str = Field(index=True)
    resume_text: str = ""
    stage: Stage = Field(default=Stage.applied, index=True)
    source: Optional[str] = None
    archived: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)

    # AI summary is stored as JSON text so the module's output shape can evolve
    # without a migration. NULL means "never generated".
    summary_json: Optional[str] = None
    summary_generated_at: Optional[datetime] = None


class Note(SQLModel, table=True):
    """Append-only: no update or delete route exists for notes by design."""

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidate.id", index=True)
    text: str
    created_at: datetime = Field(default_factory=utcnow)
