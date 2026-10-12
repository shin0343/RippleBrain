# Architecture

## Overview
Next.js frontend → FastAPI backend → { HydraDB (when configured) | transparent local retrieval } + SQLite persistence. An agentic orchestrator selects tools per request and drafts approval-gated actions.

```
[Next.js UI] --REST--> [FastAPI /api/*] --> [Orchestrator]
                                                |-> search_company_knowledge (HydraDB query or local hybrid)
                                                |-> retrieve_related_entities (Hydra graph paths or manifest graph)
                                                |-> compare_policy_versions (regex + date extraction)
                                                |-> detect_conflicts (stale-doc + contract-override rules, injection scan)
                                                |-> prepare_action_tasks (idempotent drafts -> SQLite)
                                                |-> record_approved_decision (HydraDB memory or local memory)
```

## HydraDB integration (verified against SDK `hydradb-sdk>=2.1.1,<3` and Oct-2026 tutorial)
- `client.databases.create` / `client.databases.status` (bounded provisioning wait, no infinite retry)
- `client.context.ingest` with `type="knowledge"`, `document_metadata`, `graph_payload` (manifest declares SUPERSEDES/IMPACTS/OVERRIDES/OWNED_BY/ASSIGNED_TO with evidence contexts)
- `client.context.ingest` with `type="memory"` for approval records
- `client.context.status` polling until `completed` (timeout + error surfacing)
- `client.query` with `type="knowledge"`, `query_by="hybrid"`, `mode="thinking"` + `graph_context=True` (advanced) vs `graph_context=False` (baseline); `type="all"` pattern reserved for knowledge+memory merge
- `build_string` pattern: chunks + graph paths formatted as grounded LLM context (LLM generation only when `OPENAI_API_KEY` set)

## Retrieval modes
- **hydra**: real HydraDB chunks + graph paths, labeled as such in UI/API.
- **local**: TF-IDF/keyword hybrid over `data/company/*.md` + `data/relationships/graph.json`, always labeled `retrieval_mode: "local"` — never presented as HydraDB.

## Agent
- Planner: OpenAI function-calling when `OPENAI_API_KEY` set; otherwise rule-based conditional planner (selects subset based on request content; `detect_conflicts` is a mandatory safety gate before any action draft).
- State recorded per analysis: request_id, selected_tools, tool_results, retrieved_sources, relations, impacts, exceptions, proposed_actions, approval_status, execution_log, errors.
- Safety: drafts only; approve/reject transitions gated on `draft` status; idempotency keys prevent duplicate creation on retry/double-click; embedded document instructions are treated as data and flagged, never executed.

## Persistence
- SQLite (`data/ripplebrain.db`): analyses, actions (with evidence JSON + approval notes), activity log, local memory. Knowledge originals are never overwritten — approvals append to Memory/Action Log.
