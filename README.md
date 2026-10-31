# Candidate Tracker

A small applicant tracking system: add candidates, move them through a hiring pipeline, keep timestamped notes, and generate an AI summary of each resume.

**Stack:** FastAPI + SQLModel (SQLite) backend, React + TypeScript (Vite) frontend, Anthropic Claude for the summary.

## Run it

Needs Python 3.11+ and Node 18+.

```bash
# 1. Backend (terminal 1)
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then put your key in .env (optional, see below)
python seed.py                  # loads 6 sample candidates (safe to re-run)
uvicorn app.main:app --reload   # http://127.0.0.1:8000  (API docs at /docs)

# 2. Frontend (terminal 2)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

The app works without an API key; only "Generate summary" needs `ANTHROPIC_API_KEY` and shows a clear message if it is missing.

## Tests

```bash
cd backend && python -m pytest -q     # 20 tests, no network, no API key needed
cd frontend && npm test               # 2 tests
```

The model is faked in tests, so they check how this code handles inputs and outputs, not how good the model's summaries are. See "What the tests do not cover" in `docs/WRITEUP.md`.

## Where things are

| Path | What |
|---|---|
| `backend/app/main.py` | REST routes (candidates, stage, notes, archive, delete, summary) |
| `backend/app/models.py` | `Candidate`, `Note` tables and the `Stage` enum |
| `backend/app/ai_summary/` | **The AI module**: `sanitize.py` (input checks), `prompt.py` (prompt), `service.py` (API call + output validation), `schema.py` (output shape) |
| `frontend/src/components/SummaryPanel.tsx` | The AI module's UI, a self-contained component |
| `backend/seed_data/` | Stand-in seed data, including a garbled resume and two prompt-injection resumes |

## Docs

`docs/WRITEUP.md` (design and AI integration), `docs/AI_USAGE_LOG.md`, `docs/LEARNING_LOG.md`, `docs/DEPLOYMENT.md`.

## Notes

- Seed data is a stand-in I wrote, because the shared seed set was not available when I built this.
- File upload accepts `.txt` / `.md` only; for a PDF, paste the text. See the write-up for why.
