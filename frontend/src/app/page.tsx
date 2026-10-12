"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Action, type Evidence, type ExceptionItem, type Impact } from "@/lib/api";

const DEMO_CHANGE =
  "Our refund policy changes from 30 days to 14 days effective October 15, 2026. Analyze the organizational impact.";

type Status = {
  hydra_configured: boolean; hydra_connected: boolean; retrieval_mode: string;
  indexed_sources: number; message: string;
};
type Analysis = {
  analysis_id: string; retrieval_mode: string; summary: string;
  old_window_days: number | null; new_window_days: number | null; effective_date: string | null;
  impacts: Impact[]; exceptions: ExceptionItem[]; actions: Action[];
  sources: Evidence[]; graph: Record<string, unknown>;
  selected_tools: string[]; execution_log: string[]; warnings: string[];
};

function sevColor(s: string) {
  if (s === "High") return "bg-red-100 text-red-800";
  if (s === "Medium") return "bg-amber-100 text-amber-800";
  return "bg-emerald-100 text-emerald-800";
}

function EvidenceList({ items }: { items: Evidence[] }) {
  if (!items?.length) return <p className="text-sm text-slate-500">No evidence.</p>;
  return (
    <ul className="space-y-2">
      {items.map((e, i) => (
        <li key={i} className="rounded-lg bg-slate-50 p-2.5 text-xs leading-relaxed">
          <span className="font-semibold text-ink">{e.title}</span>
          <span className="text-slate-400"> · {e.source_id}</span>
          <p className="mt-1 text-slate-600">{e.excerpt}</p>
        </li>
      ))}
    </ul>
  );
}

export default function Page() {
  const [status, setStatus] = useState<Status | null>(null);
  const [sources, setSources] = useState<{ id: string; title: string; department: string; status: string }[]>([]);
  const [input, setInput] = useState(DEMO_CHANGE);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [actions, setActions] = useState<Action[]>([]);
  const [activity, setActivity] = useState<{ id: number; kind: string; message: string; created_at: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState("");
  const [phase, setPhase] = useState("");
  const [note, setNote] = useState("");
  const [approving, setApproving] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, src, act, ac] = await Promise.all([
        api.brainStatus(), api.sources(), api.activity(), api.actions().catch(() => ({ actions: [] })),
      ]);
      setStatus(s); setSources(src); setActivity(act);
      if (ac?.actions) setActions(ac.actions);
    } catch (e) {
      setError(`Backend unreachable. Start it with: backend/.venv/bin/uvicorn app.main:app --app-dir backend (port 8000). ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  async function onSeed() {
    setSeeding(true); setError("");
    try { await api.seed(); await refresh(); }
    catch (e) { setError((e as Error).message); }
    finally { setSeeding(false); }
  }

  async function onAnalyze() {
    if (loading || input.trim().length < 10) return;
    setLoading(true); setError(""); setAnalysis(null);
    const steps = ["Retrieving company context", "Identifying policy changes", "Tracing affected relationships", "Detecting exceptions", "Preparing actions"];
    try {
      for (const s of steps) { setPhase(s + "…"); await new Promise((r) => setTimeout(r, 250)); }
      const res: Analysis = await api.analyze(input);
      setAnalysis(res);
      setActions(res.actions?.length ? res.actions : actions);
      setPhase("");
      const ac = await api.actions().catch(() => null);
      if (ac?.actions) setActions(ac.actions);
      const act = await api.activity().catch(() => null);
      if (act) setActivity(act);
    } catch (e) { setError((e as Error).message); setPhase(""); }
    finally { setLoading(false); }
  }

  async function onDecision(id: string, decision: "approve" | "reject") {
    setApproving(id); setError("");
    try {
      if (decision === "approve") await api.approve(id, note);
      else await api.reject(id, note);
      const ac = await api.actions();
      setActions(ac.actions);
      setActivity(await api.activity());
    } catch (e) { setError((e as Error).message); }
    finally { setApproving(null); }
  }

  const pending = useMemo(() => actions.filter((a) => a.status === "draft"), [actions]);
  const done = useMemo(() => actions.filter((a) => a.status !== "draft"), [actions]);
  const graphRels: { source: string; predicate: string; target: string }[] = useMemo(() => {
    const g = analysis?.graph as { relations?: { source: string; target: string; predicate: string }[] } | null;
    return (g?.relations || []).slice(0, 12).map((r) => ({ source: r.source, predicate: r.predicate, target: r.target }));
  }, [analysis]);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-navy text-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-cyanx">Northstar Cloud · Synthetic demo data</p>
            <h1 className="mt-1 text-2xl font-bold sm:text-3xl">RippleBrain</h1>
            <p className="text-sm text-slate-300">One Change. Every Impact. Zero Blind Spots.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary !bg-electric" onClick={onAnalyze} disabled={loading}>Analyze a Change</button>
            <button className="btn-secondary !bg-white/10 !text-white !border-white/20 hover:!bg-white/20" onClick={() => { setInput(DEMO_CHANGE); window.scrollTo({ top: 400 }); }}>Explore Demo Company</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6">
        {error && <div role="alert" className="card border-red-300 bg-red-50 p-4 text-sm text-red-800">{error}</div>}

        {/* Status row */}
        <section className="grid gap-4 md:grid-cols-4">
          <div className="card p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Company Brain</p>
            <p className="mt-1 font-bold">{status ? (status.hydra_connected ? "HydraDB connected" : "Local mode (transparent)") : "…"}</p>
            <p className="mt-1 text-xs text-slate-500">{status?.message || "Checking connection…"}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Indexed sources</p>
            <p className="mt-1 text-2xl font-bold">{status?.indexed_sources ?? "…"}</p>
            <p className="text-xs text-slate-500">Knowledge + manifest graph</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Impacted departments</p>
            <p className="mt-1 text-2xl font-bold">{analysis ? analysis.impacts.length : "—"}</p>
            <p className="text-xs text-slate-500">{!analysis ? "Run an analysis" : analysis.old_window_days == null ? "No policy window extracted — see result below" : `${analysis.old_window_days}d → ${analysis.new_window_days}d · eff. ${analysis.effective_date}`}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Pending approvals</p>
            <p className="mt-1 text-2xl font-bold">{pending.length}</p>
            <p className="text-xs text-slate-500">{done.length} decided</p>
          </div>
        </section>

        {/* Change input */}
        <section className="card p-5" aria-label="Change analysis">
          <h2 className="text-lg font-bold">Change → Impact → Action</h2>
          <p className="text-sm text-slate-500">Describe the policy change in plain language. The agent retrieves Company Brain context, traces relationships, and drafts reviewable actions.</p>
          <label htmlFor="change" className="mt-3 block text-sm font-semibold">Change request</label>
          <textarea id="change" rows={3} value={input} onChange={(e) => setInput(e.target.value)}
            className="mt-1 w-full rounded-xl border border-slate-300 p-3 text-sm focus:border-electric focus:outline-none" />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button className="btn-primary" onClick={onAnalyze} disabled={loading || input.trim().length < 10}>
              {loading ? "Analyzing…" : "Analyze impact"}
            </button>
            <button className="btn-secondary" onClick={onSeed} disabled={seeding}>{seeding ? "Loading…" : "Load sample data"}</button>
            {phase && <span aria-live="polite" className="text-sm font-medium text-electric">{phase}</span>}
          </div>
          {analysis && (
            <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm">
              <p><span className="font-semibold">Result:</span> {analysis.summary}</p>
              <p className="mt-1 text-xs text-slate-500">Retrieval: <span className="font-semibold">{analysis.retrieval_mode === "hydra" ? "HydraDB (knowledge + graph context)" : "Local fallback — not presented as HydraDB"}</span> · Tools: {analysis.selected_tools.join(", ")}</p>
              {analysis.warnings?.length > 0 && <p className="mt-1 text-xs text-amber-700">Notes: {analysis.warnings.join(" ")}</p>}
              <details className="mt-2 text-xs text-slate-600"><summary className="cursor-pointer font-semibold">Technical details (tool calls)</summary>
                <ul className="mt-1 list-disc pl-5">{analysis.execution_log.map((l, i) => <li key={i}>{l}</li>)}</ul>
              </details>
            </div>
          )}
        </section>

        {/* Impacts */}
        {analysis && (
          <section aria-label="Organizational impact">
            <h2 className="mb-2 text-lg font-bold">Organizational impact <span className="text-sm font-normal text-slate-500">({analysis.impacts.length} teams may be affected)</span></h2>
            <div className="grid gap-4 md:grid-cols-2">
              {analysis.impacts.map((imp) => (
                <article key={imp.department} className="card p-4">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-bold">{imp.department}</h3>
                    <span className={`badge ${sevColor(imp.severity)}`}>{imp.severity}{imp.verified ? "" : " · Needs review"}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-700">{imp.description}</p>
                  <p className="mt-2 text-xs"><span className="font-semibold">Docs:</span> {imp.affected_documents.join(" · ")}</p>
                  <p className="text-xs"><span className="font-semibold">Owner:</span> {imp.owner}</p>
                  <p className="mt-1 text-xs text-tealx"><span className="font-semibold">Next:</span> {imp.recommended_action}</p>
                  <details className="mt-2"><summary className="cursor-pointer text-xs font-semibold text-electric">Evidence ({imp.evidence.length})</summary>
                    <div className="mt-2"><EvidenceList items={imp.evidence} /></div>
                  </details>
                </article>
              ))}
            </div>
          </section>
        )}

        {/* Exceptions */}
        {analysis && analysis.exceptions.length > 0 && (
          <section aria-label="Exceptions and risks" className="card border-amber-300 p-5">
            <h2 className="text-lg font-bold">Exceptions & risks</h2>
            {analysis.exceptions.map((ex, i) => (
              <article key={i} className="mt-3 rounded-xl bg-amber-50 p-4">
                <h3 className="font-bold text-amber-900">{ex.title}</h3>
                <p className="mt-1 text-sm text-amber-900">{ex.explanation}</p>
                <p className="mt-1 text-xs text-amber-800">Clause {ex.clause} · applies through {ex.applies_through}</p>
                <details className="mt-2"><summary className="cursor-pointer text-xs font-semibold">Contract evidence</summary>
                  <div className="mt-2"><EvidenceList items={ex.evidence} /></div>
                </details>
              </article>
            ))}
          </section>
        )}

        {/* Actions */}
        <section aria-label="Action center" className="card p-5">
          <h2 className="text-lg font-bold">Action center <span className="text-sm font-normal text-slate-500">(human approval required — drafts never self-apply)</span></h2>
          <label htmlFor="note" className="mt-2 block text-xs font-semibold text-slate-600">Approval note (optional, stored with decision)</label>
          <input id="note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. FAQ wording verified with Legal"
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm" />
          <div className="mt-3 space-y-3">
            {actions.length === 0 && <p className="text-sm text-slate-500">No actions yet — run an analysis to generate reviewable drafts.</p>}
            {actions.map((a) => (
              <article key={a.id} className="rounded-xl border border-slate-200 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold">{a.title}</h3>
                  <span className={`badge ${a.status === "draft" ? "bg-slate-200 text-slate-700" : a.status === "approved" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"}`}>{a.status}</span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{a.description}</p>
                <p className="mt-1 text-xs text-slate-500">{a.department} · {a.owner} · {a.priority} priority{a.approval_note ? ` · note: ${a.approval_note}` : ""}</p>
                {a.status === "draft" ? (
                  <div className="mt-2 flex gap-2">
                    <button className="btn-primary !px-4 !py-2 text-sm" disabled={approving === a.id} onClick={() => onDecision(a.id, "approve")}>Approve</button>
                    <button className="btn-secondary !px-4 !py-2 text-sm" disabled={approving === a.id} onClick={() => onDecision(a.id, "reject")}>Reject</button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </section>

        {/* Knowledge + graph */}
        <section className="grid gap-4 md:grid-cols-2">
          <div className="card p-5" aria-label="Knowledge explorer">
            <h2 className="text-lg font-bold">Knowledge explorer</h2>
            <p className="text-xs text-slate-500">{sources.length} indexed documents · Knowledge vs Memory separated (approvals → Memory)</p>
            <ul className="mt-2 max-h-72 space-y-1.5 overflow-auto text-xs">
              {sources.map((s) => (
                <li key={s.id} className="rounded-lg bg-slate-50 p-2"><span className="font-semibold">{s.title}</span><br /><span className="text-slate-500">{s.id} · {s.department} · {s.status}</span></li>
              ))}
            </ul>
          </div>
          <div className="card p-5" aria-label="Relationship graph">
            <h2 className="text-lg font-bold">Relationship evidence</h2>
            <p className="text-xs text-slate-500">Source: {analysis ? (analysis.retrieval_mode === "hydra" ? "HydraDB graph context" : "local manifest (not HydraDB)") : "run an analysis to load relations"}</p>
            {graphRels.length === 0 ? <p className="mt-2 text-sm text-slate-500">No relations loaded yet.</p> : (
              <ul className="mt-2 max-h-72 space-y-1.5 overflow-auto font-mono text-xs">
                {graphRels.map((r, i) => <li key={i} className="rounded bg-slate-900 p-2 text-cyan-200">{r.source} <span className="text-amber-300">—[{r.predicate}]→</span> {r.target}</li>)}
              </ul>
            )}
          </div>
        </section>

        {/* Activity */}
        <section className="card p-5" aria-label="Recent activity">
          <h2 className="text-lg font-bold">Recent activity</h2>
          <ul className="mt-2 space-y-1 text-xs text-slate-600">
            {activity.slice(0, 12).map((a) => <li key={a.id}><span className="font-mono text-slate-400">{a.created_at}</span> · <span className="font-semibold">{a.kind}</span> · {a.message}</li>)}
            {activity.length === 0 && <li>No activity yet.</li>}
          </ul>
        </section>

        <footer className="pb-8 text-center text-xs text-slate-400">RippleBrain hackathon MVP · Synthetic demo data · Approval-gated actions · No real customer data</footer>
      </main>
    </div>
  );
}
