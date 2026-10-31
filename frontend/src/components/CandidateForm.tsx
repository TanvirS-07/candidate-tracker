import { useState, type FormEvent } from "react";
import { api } from "../api";

const SOURCES = ["", "Referral", "LinkedIn", "Careers page", "Job board", "Other"];
const MAX_UPLOAD_BYTES = 200_000;

export default function CandidateForm({ onCreated, onCancel }: { onCreated: (id: number) => void; onCancel: () => void }) {
  const [form, setForm] = useState({ name: "", email: "", phone: "", role: "", source: "", resume_text: "" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  // File upload is read in the browser and dropped into the text box, so the user can see and
  // fix what will be stored. Plain text only; see README for why PDF parsing was left out.
  async function onFile(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_UPLOAD_BYTES) return setError("File is too large (200 KB max).");
    if (!/\.(txt|md)$/i.test(file.name)) return setError("Only .txt and .md files are supported. Paste the text instead.");
    setError(null);
    setForm((f) => ({ ...f, resume_text: "" }));
    const text = await file.text();
    setForm((f) => ({ ...f, resume_text: text }));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await api.create({
        ...form,
        phone: form.phone || undefined,
        source: form.source || undefined,
      });
      onCreated(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="card form">
      <h2>New candidate</h2>
      <label>
        Name *
        <input required value={form.name} onChange={set("name")} />
      </label>
      <label>
        Email *
        <input required type="email" value={form.email} onChange={set("email")} />
      </label>
      <label>
        Phone
        <input value={form.phone} onChange={set("phone")} />
      </label>
      <label>
        Role applied for *
        <input required value={form.role} onChange={set("role")} />
      </label>
      <label>
        Source
        <select value={form.source} onChange={set("source")}>
          {SOURCES.map((s) => (
            <option key={s} value={s}>
              {s || "—"}
            </option>
          ))}
        </select>
      </label>
      <label>
        Resume / cover letter (paste text)
        <textarea rows={10} value={form.resume_text} onChange={set("resume_text")} />
      </label>
      <label>
        …or upload a .txt / .md file
        <input type="file" accept=".txt,.md,text/plain,text/markdown" onChange={(e) => onFile(e.target.files?.[0])} />
      </label>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="row">
        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save candidate"}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
