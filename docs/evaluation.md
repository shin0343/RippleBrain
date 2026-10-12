# Evaluation

Two rounds executed 2026-10-12 (UTC): Round 1 without keys (transparent local mode), Round 2 with a live `HYDRA_DB_API_KEY` (provided during the session).

## Functional QA (Round 2, live key; local-mode equivalents re-verified with key blanked)

| # | Scenario | Result |
|---|---|---|
| A | Policy change 30→14d, eff. 2026-10-15 | PASS (both modes) — 4/4 departments (Support High, Sales High, Finance Medium, Legal High), 8–10 cited sources |
| B | ACME contract exception | PASS (both modes) — Sec 7.3 through 2026-12-31, "should not automatically override"; never auto-overwritten |
| C | Agent actions | PASS — 4 drafts, correct owners, `draft` status, SQLite-persisted; re-run creates 0 duplicates (content-based idempotency keys) |
| D | Human approval | PASS — draft→approved/rejected only; notes + audit log + local memory stored and re-queryable; HydraDB memory reported as `local` (not claimed) |
| E | Missing evidence (parental-leave probe) | PASS (local) — 0 impacts / 0 actions, explicit "Insufficient evidence" warning (gate: top score 0.652 < 0.8 threshold); live-Hydra variant NOT VERIFIED |
| V1/V2 | Variant queries (ACME-focused; wording-update) | PASS — retrieval actually varies by query (different rankings/sources); non-fixed output confirmed. Requests without day-values use disclosed corpus defaults (logged) |
| Inj | Prompt injection (embedded "skip approvals" bait) | PASS (local) — surfaced as "Untrusted instruction ignored", approval gate intact. Live-Hydra chunk windows cover doc starts only, so the doc-end bait is out of window there (logged limitation, gate intact) |

## Regression

| Check | Command | Result |
|---|---|---|
| Backend tests (local, key blanked) | `backend/.venv/bin/python -m pytest backend/tests -q` | **12 passed** |
| Backend tests (live key, DB unseeded→seeded) | same | **10 passed, 2 skipped** (skips are local-window-specific) |
| TypeScript | `./node_modules/.bin/tsc --noEmit` | clean |
| Lint | `./node_modules/.bin/next lint --dir src` | no warnings/errors |
| Production build | `npm run build` | OK |
| Browser E2E (Playwright + system Chrome) | `backend/.venv/bin/python /tmp/rb_e2e.py` | **14/14** incl. approve + reload persistence, mobile 390px (no overflow), zero console errors |
| API smoke | `/api/health`, `/api/brain/status`, `/api/brain/seed`, analyze→approve→activity | all OK |

## HydraDB live verification (Round 2)

- Key validated via `databases.list` (10ms latency).
- `databases.create ripplebrain_demo` + `databases.status` → `ready_for_ingestion: True`. VERIFIED.
- `context.ingest` × 12 (`type="knowledge"`, `document_metadata`, `graph_payload` on manifest) → `context.list` confirms 12/12 sources. VERIFIED. (One real bug found and fixed: top-level `title` in `document_metadata` rejected with 400; title now lives in `additional_metadata`.)
- Live hybrid retrieval (`query_by="hybrid"`, baseline) returns 10 correctly ranked chunks (Refund Policy v2 first) and drives full analysis (`retrieval_mode: hydra`). VERIFIED.
- Indexing reached `graph_creation`/`queued`, 0/12 `completed` at last check → `graph_context` query paths empty; baseline-vs-graph comparison NOT VERIFIED yet. Re-run `scripts/verify_hydradb.py` once `completed`.
- HydraDB memory ingest NOT VERIFIED (deferred until after retrieval indexing completes).

## Bugs found and fixed during this QA

1. Scenario E fabricated a full refund analysis for an unrelated query → added evidence gate (refuse below top-score 0.8 local / empty any-mode). Covered by `test_insufficient_evidence_no_fabrication`.
2. Re-running an analysis duplicated the 4 actions (keys included `analysis_id`) → content-based idempotency keys. Covered by `test_rerun_creates_no_duplicates` + live re-run check (4→4).
3. Injection bait never surfaced live (420-char excerpt truncation) → quarantine-snippet surfacing in local retrieval. Covered by `test_injection_surfaced_in_live_retrieval`.
4. `databases.status` 404 for a never-created DB misreported as "unreachable" → reachability probe via `databases.list` ("reachable, needs seed").
5. Planner invoked the LLM twice per analysis → single call, accurate planner label.
6. Missing favicon → 404 console error → added `src/app/icon.svg` (E2E check 12 now passes).
7. Null policy windows rendered as "nulld" → guarded UI copy.

No invented accuracy percentages. Anything marked NOT VERIFIED above was not executed successfully.

## Round 3 — live-key verification with promo-code access (2026-10-12, continued)

- Connection: `databases.list` OK; DB `ripplebrain_demo` provisioned (`ready_for_ingestion: True`).
- Knowledge: 12/12 sources ingested and confirmed via `context.list`; live hybrid retrieval returns 10 correctly ranked chunks driving full analyses (`retrieval_mode: hydra`).
- Graph: manifest re-ingested with corrected `graph_payload` key (two live 400s diagnosed and fixed: metadata shape, key mismatch). Indexing still `queued` 12/12 after ~1h; `relations` empty, `query_paths` empty → graph-context traversal NOT VERIFIED. Seed route now skips re-ingest when 12 sources exist (upserts were resetting indexing progress).
- Memory: approval → HydraDB memory id returned (`memory_status: hydra`); `type="all"` recall returns prior approval memories; targeted memory-collection query retrieves the newest approval. Cross-session durability confirmed.
- Regression: pytest 10 passed + 2 skipped (live mode), tsc clean, lint clean, Playwright 14/14 (fresh-state harness with local DB reset; Cloud data untouched).
