"""Load sample candidates: `python seed.py`. Skips emails that already exist, so it is safe to re-run."""

import json
from pathlib import Path

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Candidate, Stage

DATA = Path(__file__).parent / "seed_data" / "candidates.json"


def main() -> None:
    init_db()
    added = 0
    with Session(engine) as session:
        for row in json.loads(DATA.read_text(encoding="utf-8")):
            if session.exec(select(Candidate).where(Candidate.email == row["email"])).first():
                continue
            session.add(Candidate(**{**row, "stage": Stage(row["stage"])}))
            added += 1
        session.commit()
    print(f"Seeded {added} candidate(s).")


if __name__ == "__main__":
    main()
