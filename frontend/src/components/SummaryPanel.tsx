/**
 * AI summary module (frontend half). Self-contained: it receives the current summary and a
 * `generate` function, and knows nothing about the rest of the candidate page.
 * Backend half: backend/app/ai_summary/.
 */
import { useState } from "react";
import type { CandidateSummary } from "../types";

interface Props {
  summary: CandidateSummary | null;
  generatedAt: string | null;
  hasResume: boolean;
  generate: () => Promise<void>;
}

export default function SummaryPanel({ summary, generatedAt, hasResume, generate }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await generate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-labelledby="summary-heading">
      <div className="row">
        <h2 id="summary-heading">AI summary</h2>
        <button onClick={run} disabled={busy || !hasResume}>
          {busy ? "Generating…" : summary ? "Regenerate" : "Generate summary"}
        </button>
      </div>
      {!hasResume && <p className="muted">Add resume text to this candidate to enable summaries.</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {summary && (
        <div>
          {summary.injection_detected && (
            <p role="status" className="warning">
              ⚠ This resume contains text aimed at an AI or reviewer. It was ignored. Read the original before relying
              on this summary.
            </p>
          )}
          <p>
            <strong>{summary.headline}</strong>
          </p>
          <h3>Key skills</h3>
          <ul className="chips">
            {summary.key_skills.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
          <h3>Experience highlights</h3>
          <ul>
            {summary.experience_highlights.map((h) => (
              <li key={h}>{h}</li>
            ))}
          </ul>
          {summary.flags.length > 0 && <p className="muted">Notes: {summary.flags.join(" ")}</p>}
          <p className="muted">
            AI-generated{generatedAt ? ` ${new Date(generatedAt).toLocaleString()}` : ""}. Verify against the resume.
          </p>
        </div>
      )}
    </section>
  );
}
