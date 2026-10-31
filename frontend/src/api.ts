import type { CandidateDetail, CandidateListItem, NewCandidate, Stage } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    // FastAPI sends {detail: string} for our errors and {detail: [{msg}]} for validation errors.
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* non-JSON error body: keep the generic message */
    }
    throw new Error(message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const send = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  list: (p: { stage?: string; role?: string; sort: string; includeArchived: boolean }) => {
    const q = new URLSearchParams({ sort: p.sort });
    if (p.stage) q.set("stage", p.stage);
    if (p.role) q.set("role", p.role);
    if (p.includeArchived) q.set("include_archived", "true");
    return request<CandidateListItem[]>(`/candidates?${q}`);
  },
  roles: () => request<string[]>("/roles"),
  get: (id: number) => request<CandidateDetail>(`/candidates/${id}`),
  create: (c: NewCandidate) => request<CandidateDetail>("/candidates", send("POST", c)),
  setStage: (id: number, stage: Stage) => request<CandidateDetail>(`/candidates/${id}/stage`, send("PATCH", { stage })),
  setArchived: (id: number, archived: boolean) =>
    request<CandidateDetail>(`/candidates/${id}/archive`, send("PATCH", { archived })),
  remove: (id: number) => request<void>(`/candidates/${id}`, send("DELETE")),
  addNote: (id: number, text: string) => request<CandidateDetail>(`/candidates/${id}/notes`, send("POST", { text })),
  generateSummary: (id: number) => request<CandidateDetail>(`/candidates/${id}/summary`, send("POST")),
};
