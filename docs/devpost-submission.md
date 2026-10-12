# Devpost Submission Draft

## Inspiration
Policy changes ripple through enterprises — FAQs, sales decks, SOPs, contracts — but nobody sees the full blast radius. We wanted a Company Brain that turns one change into coordinated, human-approved action.

## What it does
RippleBrain analyzes a plain-language change request against company knowledge (policies, contracts, FAQs, SOPs, owners + relationship graph), surfaces per-department impacts with cited evidence, flags contractual exceptions (e.g., ACME Corp's signed 30-day term through Dec 31, 2026), and drafts assignable follow-up tasks that only take effect after human approval. Approvals are logged as persistent memory.

## How I built it
Digo App-Starter: authentication, organization workspaces, and role-based access control, integrated with RippleBrain's existing analysis engine — login as an org member, open RippleBrain inside the workspace, run analyses through an org-gated NestJS gateway that proxies the engine and audits every run per organization. (Demo scope: single organization; engine stores are shared, access is org-gated.)

HydraDB: live hybrid knowledge retrieval, verified graph relationships, and persistent decision memory.

RippleBrain: policy impact analysis, conflict detection, task generation, and human approval.

FastAPI + Next.js + SQLite. HydraDB Python SDK for knowledge ingestion (12 synthetic Northstar Cloud docs with `document_metadata`, plus a `graph_payload` declaring SUPERSEDES/IMPACTS/OVERRIDES/OWNED_BY/ASSIGNED_TO relations with evidence contexts), provisioning/indexing status polling, and hybrid retrieval (`query_by="hybrid"`, `mode="thinking"`, `graph_context` on/off). A tool-calling agent (OpenAI function-calling when keyed, otherwise a conditional rule planner — never a fixed script) runs search → compare → relations → conflict detection (mandatory gate, plus an insufficient-evidence refusal gate) → idempotent action drafting. Human approval flips real database state; approvals append to Memory, never silently overwrite Knowledge. Without a HydraDB key the app runs a clearly labeled local fallback — never presented as HydraDB results.

## Challenges I ran into
Async HydraDB indexing on hackathon night (provisioning/indexing waits with timeouts instead of infinite retries); a live 400 that taught me `document_metadata` rejects top-level `title`; keeping graph relations grounded in source docs rather than decor; approval safety (content-based idempotency so re-runs never duplicate work, draft-only writes, injection-bearing docs treated as data); an out-of-corpus query that exposed fabricated impacts, fixed with a retrieval-score refusal gate.

## Accomplishments that I'm proud of
A verified end-to-end loop — Change → Impact → Exception → Draft → Approve → Memory — against a **live HydraDB database** (12/12 sources ingested, live hybrid retrieval driving the analysis), with cited evidence, transparent retrieval labeling, 12/12 tests passing, and 14/14 browser checks green.

## What I learned
Live APIs beat assumptions: the real HydraDB error messages fixed two integration bugs in minutes. Explicit BYO-graph edges make compliance-critical relations (like contract overrides) deterministic, and refusal gates matter as much as generation quality.

## What's next
Full graph-context comparison once indexing completes, HydraDB-backed approval memories, Slack/Jira ingestion, multi-policy scenarios, and org-role memories.
