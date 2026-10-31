from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.ai_summary import Summarizer, get_summarizer
from app.db import get_session
from app.main import app

GOOD_RESUME = (
    "Priya Nair. Graduate software engineer. Built a React and TypeScript dashboard and FastAPI "
    "endpoints backed by PostgreSQL during a six month internship. Wrote pytest tests and a GitHub "
    "Actions pipeline. Skills: Python, TypeScript, React, FastAPI, PostgreSQL, Git."
)

GOOD_TOOL_INPUT = {
    "headline": "Graduate engineer with React and FastAPI internship experience.",
    "key_skills": ["Python", "React", "FastAPI"],
    "experience_highlights": ["Built a React dashboard during a six month internship"],
    "injection_detected": False,
    "flags": [],
}


class FakeAnthropic:
    """Stands in for anthropic.Anthropic. Records every call so tests can inspect the prompt."""

    def __init__(self, tool_input=None, raises=None, blocks=None):
        self.calls = []
        self._tool_input = GOOD_TOOL_INPUT if tool_input is None else tool_input
        self._raises = raises
        self._blocks = blocks
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._raises:
            raise self._raises
        blocks = self._blocks if self._blocks is not None else [SimpleNamespace(type="tool_use", input=self._tool_input)]
        return SimpleNamespace(content=blocks)


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def fake_ai():
    return FakeAnthropic()


@pytest.fixture()
def client(session, fake_ai):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_summarizer] = lambda: Summarizer(client=fake_ai, model="test-model")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def make_candidate(client):
    def _make(**overrides):
        body = {"name": "Priya Nair", "email": "priya@example.com", "role": "Engineer", "resume_text": GOOD_RESUME}
        body.update(overrides)
        r = client.post("/api/candidates", json=body)
        assert r.status_code == 201, r.text
        return r.json()

    return _make
