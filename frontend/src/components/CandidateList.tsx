import { useEffect, useState } from "react";
import { api } from "../api";
import { STAGES, type CandidateListItem } from "../types";

export default function CandidateList({ onOpen }: { onOpen: (id: number) => void }) {
  const [rows, setRows] = useState<CandidateListItem[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [stage, setStage] = useState("");
  const [role, setRole] = useState("");
  const [sort, setSort] = useState("date");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.roles().then(setRoles).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false; // ignore out-of-order responses when filters change quickly
    api
      .list({ stage, role, sort, includeArchived })
      .then((r) => !cancelled && (setRows(r), setError(null)))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [stage, role, sort, includeArchived]);

  return (
    <section>
      <div className="filters">
        <label>
          Stage
          <select value={stage} onChange={(e) => setStage(e.target.value)}>
            <option value="">All</option>
            {STAGES.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Role
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="">All</option>
            {roles.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </label>
        <label>
          Sort by
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="date">Date added (newest)</option>
            <option value="stage">Stage</option>
          </select>
        </label>
        <label className="inline">
          <input type="checkbox" checked={includeArchived} onChange={(e) => setIncludeArchived(e.target.checked)} />
          Show archived
        </label>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {rows.length === 0 && !error && <p className="muted">No candidates match.</p>}
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Role</th>
            <th>Stage</th>
            <th>Source</th>
            <th>Added</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id} onClick={() => onOpen(c.id)} className={c.archived ? "archived" : ""}>
              <td>
                <button className="link" onClick={() => onOpen(c.id)}>
                  {c.name}
                </button>
                {c.archived && <span className="badge">archived</span>}
              </td>
              <td>{c.role}</td>
              <td>
                <span className={`stage stage-${c.stage}`}>{c.stage}</span>
              </td>
              <td>{c.source ?? "—"}</td>
              <td>{new Date(c.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
