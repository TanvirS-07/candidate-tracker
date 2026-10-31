"""Deterministic input handling that runs BEFORE any model call.

None of this is a security boundary on its own (regexes can't catch every phrasing).
The real defences are in prompt.py (untrusted-data framing) and service.py (schema-only
output, no tools with side effects). These checks save money on junk and give the
recruiter a signal that doesn't depend on the model behaving.
"""

import re
import unicodedata

MAX_CHARS = 12_000  # ~3k tokens: enough for a long resume, caps cost and attack surface
MIN_LETTERS = 80

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier)\s+(instructions|prompts?|rules)", "ignore-previous"),
    (r"disregard\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|your)\s+", "disregard"),
    (r"(recommend|hire|rank|rate|score)\s+(this\s+candidate|me)\b", "steer-outcome"),
    (r"</?\s*(resume|system|instructions?)\s*>", "delimiter-spoof"),
]


def clean(text: str) -> str:
    """Normalise to plain readable text and cap length."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.translate(_ZERO_WIDTH)
    text = _CONTROL.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_CHARS]


def quality_problem(text: str) -> str | None:
    """Return a human-readable reason if the text isn't worth sending to a model, else None."""
    letters = sum(ch.isalpha() for ch in text)
    if letters < MIN_LETTERS:
        return "Resume text is too short to summarise."
    non_space = sum(not ch.isspace() for ch in text)
    if letters / non_space < 0.6:
        return "Resume text looks garbled (mostly symbols or non-text characters)."
    return None


def injection_markers(text: str) -> list[str]:
    """Names of the suspicious patterns found. Used as a flag for the recruiter, never as a filter."""
    lowered = text.lower()
    return sorted({name for pattern, name in _INJECTION_PATTERNS if re.search(pattern, lowered)})


def neutralise_delimiters(text: str) -> str:
    """Stop resume text from closing the <resume> wrapper early and 'escaping' into the prompt."""
    return re.sub(r"<(/?)\s*resume", r"<\1_resume", text, flags=re.IGNORECASE)
