import os
from typing import Any, Optional

from pydantic import ValidationError

from . import sanitize
from .prompt import SYSTEM_PROMPT, build_user_message
from .schema import CandidateSummary

DEFAULT_MODEL = "claude-haiku-5-5"  # short extraction task: cheapest/fastest tier is enough
TOOL_NAME = "record_summary"
INJECTION_NOTE = "Resume contains text addressed to an AI or reviewer; it was ignored."

# Per-item character limits, read from the schema so they can't drift out of sync with it.
_ITEM_LIMITS = {
    field: CandidateSummary.model_json_schema()["properties"][field]["items"]["maxLength"]
    for field in ("key_skills", "experience_highlights", "flags")
}


def _truncate_long_items(tool_input: Any) -> Any:
    """Shorten over-long strings in the list fields instead of rejecting the whole summary.

    Only string length is fixed here. Anything structural (missing fields, wrong types,
    too many items) is left as-is so model_validate still rejects it.
    """
    if not isinstance(tool_input, dict):
        return tool_input
    fixed = dict(tool_input)  # don't mutate the SDK's response object
    for field, limit in _ITEM_LIMITS.items():
        items = fixed.get(field)
        if isinstance(items, list):
            fixed[field] = [
                item[: limit - 1].rstrip() + "…" if isinstance(item, str) and len(item) > limit else item
                for item in items
            ]
    return fixed


class SummaryError(Exception):
    """Carries the HTTP status the route should return."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class Summarizer:
    def __init__(self, client: Optional[Any] = None, model: Optional[str] = None):
        self._client = client
        self.model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)

    def _get_client(self):
        if self._client is None:
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise SummaryError(503, "AI summaries are not configured (ANTHROPIC_API_KEY is not set).")
            import anthropic

            self._client = anthropic.Anthropic(timeout=30.0, max_retries=2)
        return self._client

    def summarize(self, resume_text: str, role: str) -> CandidateSummary:
        text = sanitize.clean(resume_text)
        problem = sanitize.quality_problem(text)
        if problem:
            # No model call: nothing useful to send, and nothing to attack.
            raise SummaryError(422, problem)

        markers = sanitize.injection_markers(text)
        client = self._get_client()
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=700,
                system=SYSTEM_PROMPT,
                # Forcing a single side-effect-free tool constrains output to the schema.
                tools=[
                    {
                        "name": TOOL_NAME,
                        "description": "Record the structured summary of the resume.",
                        "input_schema": CandidateSummary.model_json_schema(),
                    }
                ],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[
                    {
                        "role": "user",
                        "content": build_user_message(sanitize.neutralise_delimiters(text), role),
                    }
                ],
            )
        except Exception as e:  # network, auth, rate limit: the route shows a retryable message
            raise SummaryError(502, f"The AI service is unavailable right now ({type(e).__name__}). Try again.")

        block = next((b for b in response.content if getattr(b, "type", None) == "tool_use"), None)
        if block is None:
            raise SummaryError(502, "The AI service returned no structured summary. Try again.")
        try:
            summary = CandidateSummary.model_validate(_truncate_long_items(block.input))
        except ValidationError:
            raise SummaryError(502, "The AI service returned an invalid summary. Try again.")

        # Belt and braces: our own check can raise the flag even if the model missed it.
        # Only then do we add our own note; if the model detected it, its flag already explains it.
        if markers and not summary.injection_detected:
            summary.injection_detected = True
            summary.flags = [*summary.flags, INJECTION_NOTE][:5]
        # The model detected it but wrote no note: add ours so the warning banner isn't left unexplained.
        elif summary.injection_detected and not summary.flags:
            summary.flags = [INJECTION_NOTE]
        return summary


def get_summarizer() -> Summarizer:
    """FastAPI dependency; tests override it with a Summarizer wrapping a fake client."""
    return Summarizer()
