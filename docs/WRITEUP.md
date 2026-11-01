# Write-up

## Design choices

- **Small, plain core:** two tables (`Candidate`, `Note`), one route file, a `Stage` enum. Stages can move in any direction, as the brief asks. "Sort by stage" uses pipeline order, not alphabetical, and a test pins that.
- **SQLite + SQLModel:** no setup for a reviewer. Request schemas (`schemas.py`) are kept separate from the table models, because SQLModel table classes do not validate input (see the learning log). Moving to Postgres is a `DATABASE_URL` change.
- **Notes are append-only by design:** no route exists to edit or delete one, and a test checks that. **Archive** hides a candidate and keeps everything; **delete** is permanent and asks for confirmation.
- **AI is one module:** `backend/app/ai_summary/`, plus one route and one React component (`SummaryPanel`). The rest of the app only knows "a summary is a JSON blob on the candidate".

## How the AI feature works

1. **`sanitize.py`, before any model call:** normalise Unicode, strip invisible and control characters, cap at 12,000 characters, and reject garbled or too-short text with a 422. **No model call is made** for rejected text.
2. **`prompt.py`:** the resume is marked as untrusted data inside `<resume>` tags, never to be followed as instructions. Any `<resume>` tag inside the resume is rewritten so it cannot close the wrapper early.
3. **`service.py`:** the model must answer through one tool, `record_summary`, whose input schema *is* the output shape (headline, up to 10 skills, up to 5 highlights, `injection_detected`, flags). Over-long items are shortened to their limit, then the result is validated with Pydantic. Anything structurally wrong becomes a clean 502, and the previous summary is kept.
4. **Backup injection check:** a few regexes look for obvious instruction text. If one matches and the model missed it, the code sets the flag and adds a note. If the model flagged it without a note, the code adds one, so the UI warning is never unexplained.

**Why Claude Haiku:** this is a short extraction job into a fixed schema, so the cheapest, fastest tier is enough, and forced tool use gives reliable structured output.

**Limiting the damage:** the model has no tools with side effects, can only fill short schema fields, and its output is rendered as plain text and labelled AI-generated. A successful injection could at worst make one summary wrong.

## Testing against the real model

The tests use a fake model, so I also ran 8 resumes through the real one: the 6 seed resumes plus two injections I wrote to avoid every regex (a polite English request and one in French). **No injection changed a summary,** and the model caught both of mine although the regex did not. The problems were in my code: a flag-length limit that threw away safe summaries, a duplicate warning note, and a misleading "too short" message. All three are fixed, each with a test that fails without the fix. Details and before/after screenshots: [`AI_RESULTS.md`](AI_RESULTS.md).

## Tradeoffs

- **Plain-text upload only:** PDF/DOCX parsing adds a dependency and a new failure mode (bad extraction); pasting covers this scope.
- **The regex check is incomplete:** the real-model test showed paraphrases and other languages get past it. I kept it because it is cheap, explainable and only adds a warning.
- **Summary on click, not on create:** it costs money and takes seconds, and a recruiter may never open that candidate.
- **No auth, pagination or migrations:** out of scope; tables are created on startup.

## What I would build next

1. An evaluation script that runs many resumes through the real model and checks every skill in the summary appears in the resume.
2. Prompt fixes from the real-model test: define what counts as a skill, and limit flags to unreadable text and embedded instructions.
3. A "can't reach the server" message when the backend is down, instead of "Request failed (500)".
4. Postgres with Alembic migrations, pagination, and PDF/DOCX upload.
