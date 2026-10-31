import json
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, col, select

load_dotenv()

from .ai_summary import SummaryError, Summarizer, get_summarizer  # noqa: E402
from .ai_summary.schema import CandidateSummary  # noqa: E402
from .db import get_session, init_db  # noqa: E402
from .models import Candidate, Note, Stage, utcnow  # noqa: E402
from .schemas import (  # noqa: E402
    ArchiveUpdate,
    CandidateCreate,
    CandidateDetail,
    CandidateListItem,
    NoteCreate,
    NoteOut,
    StageUpdate,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Candidate Tracker", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Order used by "sort by stage": pipeline order, not alphabetical.
STAGE_ORDER = {s: i for i, s in enumerate(Stage)}


def _get_or_404(session: Session, candidate_id: int) -> Candidate:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, "Candidate not found")
    return candidate


def _detail(session: Session, c: Candidate) -> CandidateDetail:
    notes = session.exec(
        select(Note).where(Note.candidate_id == c.id).order_by(col(Note.created_at).desc(), col(Note.id).desc())
    ).all()
    summary = CandidateSummary.model_validate(json.loads(c.summary_json)) if c.summary_json else None
    return CandidateDetail(
        **c.model_dump(exclude={"summary_json"}),
        notes=[NoteOut(**n.model_dump()) for n in notes],
        summary=summary,
    )


@app.post("/api/candidates", response_model=CandidateDetail, status_code=201)
def create_candidate(body: CandidateCreate, session: Session = Depends(get_session)):
    candidate = Candidate(**body.model_dump())
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return _detail(session, candidate)


@app.get("/api/candidates", response_model=list[CandidateListItem])
def list_candidates(
    stage: Optional[Stage] = None,
    role: Optional[str] = None,
    sort: str = Query("date", pattern="^(date|stage)$"),
    include_archived: bool = False,
    session: Session = Depends(get_session),
):
    query = select(Candidate)
    if not include_archived:
        query = query.where(Candidate.archived == False)  # noqa: E712
    if stage:
        query = query.where(Candidate.stage == stage)
    if role:
        query = query.where(Candidate.role == role)
    rows = session.exec(query.order_by(col(Candidate.created_at).desc(), col(Candidate.id).desc())).all()
    if sort == "stage":
        # Stable sort keeps newest-first within each stage.
        rows = sorted(rows, key=lambda c: STAGE_ORDER[c.stage])
    return rows


@app.get("/api/roles", response_model=list[str])
def list_roles(session: Session = Depends(get_session)):
    return session.exec(select(Candidate.role).distinct().order_by(Candidate.role)).all()


@app.get("/api/candidates/{candidate_id}", response_model=CandidateDetail)
def get_candidate(candidate_id: int, session: Session = Depends(get_session)):
    return _detail(session, _get_or_404(session, candidate_id))


@app.patch("/api/candidates/{candidate_id}/stage", response_model=CandidateDetail)
def set_stage(candidate_id: int, body: StageUpdate, session: Session = Depends(get_session)):
    c = _get_or_404(session, candidate_id)
    c.stage = body.stage
    session.add(c)
    session.commit()
    return _detail(session, c)


@app.patch("/api/candidates/{candidate_id}/archive", response_model=CandidateDetail)
def set_archived(candidate_id: int, body: ArchiveUpdate, session: Session = Depends(get_session)):
    c = _get_or_404(session, candidate_id)
    c.archived = body.archived
    session.add(c)
    session.commit()
    return _detail(session, c)


@app.delete("/api/candidates/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: int, session: Session = Depends(get_session)):
    c = _get_or_404(session, candidate_id)
    for note in session.exec(select(Note).where(Note.candidate_id == c.id)).all():
        session.delete(note)
    session.delete(c)
    session.commit()


@app.post("/api/candidates/{candidate_id}/notes", response_model=CandidateDetail, status_code=201)
def add_note(candidate_id: int, body: NoteCreate, session: Session = Depends(get_session)):
    c = _get_or_404(session, candidate_id)
    session.add(Note(candidate_id=c.id, text=body.text.strip()))
    session.commit()
    return _detail(session, c)


@app.post("/api/candidates/{candidate_id}/summary", response_model=CandidateDetail)
def generate_summary(
    candidate_id: int,
    session: Session = Depends(get_session),
    summarizer: Summarizer = Depends(get_summarizer),
):
    """The only route that touches the AI module. Everything AI-related lives in app/ai_summary."""
    c = _get_or_404(session, candidate_id)
    try:
        summary = summarizer.summarize(resume_text=c.resume_text, role=c.role)
    except SummaryError as e:
        # A failed regeneration must not wipe the previous good summary.
        raise HTTPException(e.status_code, e.message)
    c.summary_json = summary.model_dump_json()
    c.summary_generated_at = utcnow()
    session.add(c)
    session.commit()
    return _detail(session, c)
