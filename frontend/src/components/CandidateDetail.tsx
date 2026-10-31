import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import { STAGES, type CandidateDetail, type Stage } from "../types";
import SummaryPanel from "./SummaryPanel";

export default function CandidateDetailView({ id, onBack }: { id: number; onBack: () => void }) {
  const [c, setC] = useState<CandidateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");

  useEffect(() => {
    api.get(id).then(setC).catch((e) => setError(e.message));
  }, [id]);

  // Run an action that returns the updated candidate and show errors inline.
  async function act(fn: () => Promise<CandidateDetail>) {
    setError(null);
    try {
      setC(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    }
  }

  async function remove() {
    if (!window.confirm(`Permanently delete ${c?.name}? Archive instead if you may need them later.`)) return;
    try {
      await api.remove(id);
      onBack();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete.");
    }
  }

  function submitNote(e: FormEvent) {
    e.preventDefault();
    if (!note.trim()) return;
    act(() => api.addNote(id, note)).then(() => setNote(""));
  }

  if (!c) {
    return error ? (
      <p role="alert" className="error">
        {error}
      </p>
    ) : (
      <p>Loading…</p>
    );
  }

  return (
    <div>
      <button className="link" onClick={onBack}>
        ← All candidates
      </button>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <section className="card">
        <div className="row">
          <h2>
            {c.name} {c.archived && <span className="badge">archived</span>}
          </h2>
          <label className="inline">
            Stage
            <select value={c.stage} onChange={(e) => act(() => api.setStage(id, e.target.value as Stage))}>
              {STAGES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
        </div>
        <dl>
          <dt>Role</dt>
          <dd>{c.role}</dd>
          <dt>Email</dt>
          <dd>{c.email}</dd>
          <dt>Phone</dt>
          <dd>{c.phone ?? "—"}</dd>
          <dt>Source</dt>
          <dd>{c.source ?? "—"}</dd>
          <dt>Added</dt>
          <dd>{new Date(c.created_at).toLocaleString()}</dd>
        </dl>
        <div className="row">
          <button className="secondary" onClick={() => act(() => api.setArchived(id, !c.archived))}>
            {c.archived ? "Unarchive" : "Archive"}
          </button>
          <button className="danger" onClick={remove}>
            Delete
          </button>
        </div>
      </section>

      <SummaryPanel
        summary={c.summary}
        generatedAt={c.summary_generated_at}
        hasResume={c.resume_text.trim().length > 0}
        generate={async () => setC(await api.generateSummary(id))}
      />

      <section className="card">
        <h2>Resume / cover letter</h2>
        {c.resume_text ? <pre>{c.resume_text}</pre> : <p className="muted">None provided.</p>}
      </section>

      <section className="card">
        <h2>Notes</h2>
        <form onSubmit={submitNote} className="row">
          <input
            aria-label="New note"
            placeholder="Add a note (cannot be edited later)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button type="submit" disabled={!note.trim()}>
            Add note
          </button>
        </form>
        {c.notes.length === 0 && <p className="muted">No notes yet.</p>}
        <ul className="notes">
          {c.notes.map((n) => (
            <li key={n.id}>
              <time>{new Date(n.created_at).toLocaleString()}</time>
              <p>{n.text}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
