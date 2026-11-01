# Learning log: SQLModel (new to me)

## What it is

SQLModel is an ORM built on SQLAlchemy, by the author of FastAPI. One class can be both a database table (`table=True`) and a Pydantic model. I picked it because I already knew FastAPI and Pydantic but had not used an ORM with them, and I wanted to see whether having one class for both the table and the data shape makes things simpler or more confusing.

## What I read

- The SQLModel tutorial on the official docs site, mainly the sections on creating tables, sessions, and using SQLModel with FastAPI.
- Other guide pages when I got stuck, for things the tutorial only touches on, such as testing with an in-memory database.
- Claude, to explain errors and to explain why the generated code was written a certain way. I checked its explanations by running small examples myself.

## What confused me

**1. The table class does not validate its data.** I assumed that because `Candidate` is a Pydantic model, creating one with bad data would raise an error. It does not:

```python
Candidate(name=123, email="not-an-email", role=None)   # accepted, no error
CandidateCreate(name="A", email="not-an-email", role="Eng")  # ValidationError
```

A `table=True` class skips validation when it is created, so bad data can reach the database unless something checks it first. This is why the project has a separate `schemas.py` in which the API takes in `CandidateCreate`, which does validate, and only then builds the table object. At first the separate file looked like duplication; once I saw this, it made sense.

**2. Why the tests need `StaticPool`.** The tests use an in-memory SQLite database (`sqlite://`), and `conftest.py` passes `poolclass=StaticPool`. I did not understand why until I removed it and that is because the tables are created on the test's thread, but the test client runs the app on a different thread. Without `StaticPool`, that thread gets a new connection, and a new connection to an in-memory database is a brand-new empty database, so it fails with `no such table: candidate`. `StaticPool` makes every connection reuse the same one, so the app sees the tables the test created.

## How I worked it out

I made small examples that reproduced each problem instead of just reading about it. For validation, I created a `Candidate` and a `CandidateCreate` with the same bad email and compared what happened. For `StaticPool`, I created the tables, then queried from a second thread with and without it, and got `no such table` without it. Once I could make it fail on purpose, the docs and Claude's explanations made sense, because I knew what question I was really asking.

## What I would tell the next engineer

- **Validate in the request schemas, not the table models.** Never build a table object straight from user input; go through a `schemas.py` class first.
- **Keep `StaticPool` in the test setup.** Removing it gives a confusing `no such table` error, not an obvious failure.
- **There are no migrations.** `create_all` only creates missing tables; it does not add columns to existing ones. After changing a model, delete `candidates.db` and run `python seed.py` again, or add Alembic once the schema starts changing.

## Would I use it again?

Yes, for a small FastAPI app with simple CRUD like this one, because sharing types between the database and the API removes a lot of repeated code. I would think twice for a larger project: it has no migrations built in, the "one class for everything" idea breaks down quickly (I still needed separate schemas), and for complex queries you end up writing plain SQLAlchemy anyway, so you need to understand both.
