export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function req(path: string, init?: RequestInit) {
  const r = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`${r.status} ${t.slice(0, 300)}`);
  }
  return r.json();
}

export const api = {
  health: () => req("/api/health"),
  brainStatus: () => req("/api/brain/status"),
  sources: () => req("/api/brain/sources"),
  seed: () => req("/api/brain/seed", { method: "POST" }),
  analyze: (change_request: string) =>
    req("/api/changes/analyze", { method: "POST", body: JSON.stringify({ change_request }) }),
  actions: () => req("/api/actions"),
  approve: (id: string, note = "") =>
    req(`/api/actions/${id}/approve`, { method: "POST", body: JSON.stringify({ note }) }),
  reject: (id: string, note = "") =>
    req(`/api/actions/${id}/reject`, { method: "POST", body: JSON.stringify({ note }) }),
  activity: () => req("/api/activity"),
};

export type Evidence = { source_id: string; title: string; excerpt: string; score?: number | null };
export type Impact = { department: string; affected_documents: string[]; description: string; severity: string; owner: string; evidence: Evidence[]; recommended_action: string; verified: boolean };
export type ExceptionItem = { title: string; customer: string; clause: string; applies_through: string; explanation: string; evidence: Evidence[] };
export type Action = { id: string; title: string; description: string; department: string; owner: string; priority: string; evidence: Evidence[]; status: string; idempotency_key: string; approval_note: string };
