# RippleBrain — One Change. Every Impact. Zero Blind Spots.

Enterprise change-impact agent over your Company Brain. Describe a policy change in plain language; RippleBrain retrieves company knowledge, traces affected departments/documents/workflows, flags contractual exceptions, and drafts human-approved follow-up tasks.

> Fictional demo company: **Northstar Cloud**. All content is **synthetic demo data**. Demo analysis is not legal advice.

## Problem
Policy changes propagate poorly: Support FAQs, sales talk tracks, finance SOPs, and signed contracts drift out of sync. Generic RAG answers questions; RippleBrain drives **Change → Impact → Exception → Action → Approval**.

## Target users
Operations managers coordinating rollouts; Legal/Compliance, Support, Sales, Finance reviewers.

## Key differentiators
- **Grounded impact analysis**: every impact cites retrieved excerpts; unverified items are labeled, never invented.
- **Contract-exception detection**: ACME Corp's signed 30-day term (Sec 7.3 through Dec 31, 2026) is never auto-overridden by the general 14-day policy.
- **Real agentic workflow**: conditional tool selection (`search_company_knowledge`, `retrieve_related_entities`, `compare_policy_versions`, `detect_conflicts`, `prepare_action_tasks`, `record_approved_decision`), execution log exposed in UI.
- **Approval-gated actions**: drafts only; approve/reject flips real SQLite state with idempotency keys and audit log; approvals appended to Memory (never silent overwrites of Knowledge).
- **Honest retrieval labeling**: `retrieval_mode: hydra|local` everywhere. Without `HYDRA_DB_API_KEY`, the app runs a transparent local fallback — never presented as HydraDB results.

## Architecture
See `docs/architecture.md`. Next.js (App Router, TS, Tailwind) → FastAPI (`/api/*`) → Orchestrator → HydraDB SDK or local store → SQLite.

## HydraDB integration status
- SDK `hydradb-sdk` (v2 API) used per `https://hydradb.com/blog/build-company-brain-ai-agents`: `databases.create/status`, `context.ingest` (`type="knowledge"` + `document_metadata` + `graph_payload` BYO graph; `type="memory"` for approvals), `context.status` polling, `query` (`query_by="hybrid"`, `mode="thinking"` + `graph_context=True` vs `False` baseline).
- **Verified live 2026-10-12**: API key validated (`databases.list` OK); database `ripplebrain_demo` created; **12/12 sources ingested** (`context.list` confirms); live hybrid retrieval returns correctly ranked chunks (Refund Policy v2 top for the demo query) and drives the full analysis end-to-end (`retrieval_mode: hydra`, 4 impacts, ACME exception, 4 actions).
- **Pending**: sources were still indexing (`queued`/`graph_creation`, 0/12 `completed` at last check), so `graph_context` query paths are empty and the baseline-vs-graph comparison is not yet demonstrated. Re-run `scripts/verify_hydradb.py` after indexing reaches `completed`.
- Without a key, the app runs a transparent local fallback — never presented as HydraDB results. Seed: `backend/.venv/bin/python scripts/seed_company.py`; verify: `backend/.venv/bin/python scripts/verify_hydradb.py`.

## Agent workflow
Planner (OpenAI function-calling if `OPENAI_API_KEY`, else conditional rule planner) → mandatory `detect_conflicts` gate → idempotent drafts → human approve/reject → memory record. Prompt-injection content in docs is flagged as untrusted data and ignored.

## Tech stack
Next.js 14, React 18, TypeScript, Tailwind; Python 3.11, FastAPI, Pydantic, HydraDB SDK, OpenAI (optional), SQLite; pytest, tsc, Next build.

## Setup
```bash
cp .env.example .env   # add HYDRA_DB_API_KEY and OPENAI_API_KEY (both optional)
uv venv backend/.venv --python 3.11
uv pip install --python backend/.venv/bin/python -r backend/requirements.txt
backend/.venv/bin/uvicorn app.main:app --app-dir backend --port 8000
cd frontend && npm install && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Demo (60 seconds)
1. Open http://localhost:3000 → **Load sample data**.
2. Keep/paste: `Our refund policy changes from 30 days to 14 days effective October 15, 2026. Analyze the organizational impact.` → **Analyze impact**.
3. Read 4 impacts + ACME exception + evidence + tool log.
4. In Action center, add a note → **Approve** one task; verify status, activity, and memory.
5. Open Knowledge explorer + Relationship evidence (provenance labeled).

## Evaluation results
`docs/evaluation.md`. `backend/.venv/bin/python -m pytest backend/tests -q` → **12 passed** (local mode) / **10 passed + 2 skipped** (live-key mode; skips are local-window-specific). `tsc --noEmit` clean, `next lint` clean, `npm run build` OK, **14/14 Playwright browser checks** (desktop + mobile, zero console errors). Live HydraDB ingestion + hybrid retrieval verified (graph paths pending full indexing); LLM tool-calling NOT VERIFIED (no `OPENAI_API_KEY`).

## Limitations
- Local fallback scoring is keyword-based, not vector search.
- LLM synthesis requires `OPENAI_API_KEY`; otherwise deterministic analysis rules apply.
- Single-user hackathon MVP: no auth, no multi-tenancy, no external integrations.

## Future roadmap
Live HydraDB graph demo, Slack/Jira/Confluence connectors, role-based memories (`type="all"`), multi-policy scenarios, calibrated confidence, Jira/Notion action sync.
