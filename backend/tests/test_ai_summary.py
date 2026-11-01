"""AI module tests. The model is faked: these test OUR handling of inputs and outputs,
not the model's quality (that needs a live, manual check; see README)."""

import json
from types import SimpleNamespace

from app.ai_summary import Summarizer, SummaryError, get_summarizer
from app.ai_summary import sanitize
from app.ai_summary.service import INJECTION_NOTE
from app.db import get_session
from app.main import app
from fastapi.testclient import TestClient

from .conftest import GOOD_RESUME, GOOD_TOOL_INPUT, FakeAnthropic

import pytest

SEED = json.loads(
    (__import__("pathlib").Path(__file__).parents[1] / "seed_data" / "candidates.json").read_text(encoding="utf-8")
)
BY_NAME = {c["name"]: c["resume_text"] for c in SEED}


# ---- happy path through the API ----

def test_summary_is_generated_stored_and_returned(client, make_candidate, fake_ai):
    c = make_candidate()
    r = client.post(f"/api/candidates/{c['id']}/summary")
    assert r.status_code == 200
    assert r.json()["summary"]["key_skills"] == ["Python", "React", "FastAPI"]
    assert r.json()["summary_generated_at"]
    # Persisted: a fresh GET returns it without another model call.
    assert client.get(f"/api/candidates/{c['id']}").json()["summary"]["headline"].startswith("Graduate")
    assert len(fake_ai.calls) == 1


# ---- garbled / unusable input never reaches the model ----

SYMBOL_HEAVY = "x" * 100 + " #!?%" * 200  # enough letters to pass the length check, but mostly symbols


@pytest.mark.parametrize("resume", ["", "   ", "short", BY_NAME["Alex Roy"], SYMBOL_HEAVY])
def test_unusable_text_is_rejected_without_calling_the_model(client, make_candidate, fake_ai, resume):
    c = make_candidate(resume_text=resume)
    r = client.post(f"/api/candidates/{c['id']}/summary")
    assert r.status_code == 422
    assert fake_ai.calls == []


def test_normal_resume_passes_quality_gate():
    assert sanitize.quality_problem(sanitize.clean(GOOD_RESUME)) is None
    for name in ["Priya Nair", "Daniel Okafor", "Mei Lin", "Sam Whitfield"]:
        assert sanitize.quality_problem(sanitize.clean(BY_NAME[name])) is None, name


# ---- adversarial input ----

def test_injection_text_is_sent_as_quoted_data_and_flagged_even_if_model_misses_it(client, make_candidate, fake_ai):
    c = make_candidate(resume_text=BY_NAME["Sam Whitfield"])
    r = client.post(f"/api/candidates/{c['id']}/summary")
    assert r.status_code == 200
    # The fake model returned injection_detected=False; our own check must still raise the flag.
    assert r.json()["summary"]["injection_detected"] is True
    assert r.json()["summary"]["flags"]

    call = fake_ai.calls[0]
    user_msg = call["messages"][0]["content"]
    assert user_msg.count("<resume>") == 1 and user_msg.count("</resume>") == 1
    assert "untrusted" in call["system"]
    # Output is forced through one schema-only tool; no free-form text, no side-effect tools.
    assert [t["name"] for t in call["tools"]] == ["record_summary"]
    assert call["tool_choice"] == {"type": "tool", "name": "record_summary"}


def test_injection_the_model_already_flagged_is_not_flagged_twice():
    # Seen with the real model on Sam Whitfield: its flag said "instructing", not "instruction",
    # so our own warning was added as a duplicate.
    resume = BY_NAME["Sam Whitfield"]
    assert sanitize.injection_markers(sanitize.clean(resume))  # our regex fires too
    model_flag = "Resume contains embedded text instructing the AI to rate the candidate 10/10; ignored."
    fake = FakeAnthropic(tool_input={**GOOD_TOOL_INPUT, "injection_detected": True, "flags": [model_flag]})
    summary = Summarizer(client=fake).summarize(resume, "Engineer")
    assert summary.injection_detected is True
    assert summary.flags == [model_flag]


def test_injection_detected_without_a_note_gets_our_note():
    # Model-only detection (regex doesn't fire), but the model left flags empty:
    # the recruiter would see the warning banner with nothing explaining it.
    assert not sanitize.injection_markers(sanitize.clean(GOOD_RESUME))
    fake = FakeAnthropic(tool_input={**GOOD_TOOL_INPUT, "injection_detected": True, "flags": []})
    summary = Summarizer(client=fake).summarize(GOOD_RESUME, "Engineer")
    assert summary.injection_detected is True
    assert summary.flags == [INJECTION_NOTE]


def test_resume_cannot_close_the_resume_tag_early(fake_ai):
    Summarizer(client=fake_ai).summarize(BY_NAME["Jordan Blake"], "Engineer")
    user_msg = fake_ai.calls[0]["messages"][0]["content"]
    assert user_msg.count("</resume>") == 1  # only our own closing tag
    assert user_msg.rstrip().endswith("</resume>")


def test_long_input_is_truncated_before_sending(fake_ai):
    Summarizer(client=fake_ai).summarize(GOOD_RESUME + " skill" * 20_000, "Engineer")
    assert len(fake_ai.calls[0]["messages"][0]["content"]) < sanitize.MAX_CHARS + 500


# ---- model/service failures ----

def test_overlong_flag_is_truncated_instead_of_rejecting_the_summary():
    # Seen with the real model: a 215-char flag on an injection resume made the whole summary fail.
    long_flag = "x" * 250
    fake = FakeAnthropic(tool_input={**GOOD_TOOL_INPUT, "flags": [long_flag]})
    summary = Summarizer(client=fake).summarize(GOOD_RESUME, "Engineer")
    assert len(summary.flags[0]) == 200
    assert summary.flags[0].endswith("…")
    assert summary.headline == GOOD_TOOL_INPUT["headline"]


def test_invalid_model_output_is_a_clean_502_and_keeps_previous_summary(client, make_candidate, session):
    c = make_candidate()
    assert client.post(f"/api/candidates/{c['id']}/summary").status_code == 200

    bad = FakeAnthropic(tool_input={"headline": "x", "key_skills": ["a"] * 50, "experience_highlights": []})
    app.dependency_overrides[get_summarizer] = lambda: Summarizer(client=bad)
    r = client.post(f"/api/candidates/{c['id']}/summary")
    assert r.status_code == 502

    kept = client.get(f"/api/candidates/{c['id']}").json()["summary"]
    assert kept["headline"] == GOOD_TOOL_INPUT["headline"]


def test_api_exception_becomes_502_not_a_crash(fake_ai):
    s = Summarizer(client=FakeAnthropic(raises=TimeoutError("boom")))
    with pytest.raises(SummaryError) as e:
        s.summarize(GOOD_RESUME, "Engineer")
    assert e.value.status_code == 502


def test_missing_tool_block_is_a_502():
    s = Summarizer(client=FakeAnthropic(blocks=[SimpleNamespace(type="text", text="I refuse")]))
    with pytest.raises(SummaryError) as e:
        s.summarize(GOOD_RESUME, "Engineer")
    assert e.value.status_code == 502


def test_missing_api_key_is_a_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SummaryError) as e:
        Summarizer().summarize(GOOD_RESUME, "Engineer")
    assert e.value.status_code == 503
