"""AI candidate summary module. Public surface: Summarizer, get_summarizer, SummaryError."""

from .service import Summarizer, SummaryError, get_summarizer

__all__ = ["Summarizer", "SummaryError", "get_summarizer"]
