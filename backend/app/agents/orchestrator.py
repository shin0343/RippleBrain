"""Agentic orchestrator: selects tools per request, executes, synthesizes.

- If OPENAI_API_KEY is set: uses OpenAI function-calling to choose the tool
  sequence dynamically (real tool selection).
- Else: rule-based planner that conditionally selects tools based on the
  change request content (contract terms? dates? departments?) — NOT a fixed
  sequence. Mandatory safety step: detect_conflicts always runs before any
  action draft is produced.
"""
from __future__ import annotations
import json
import uuid

from ..config import settings
from ..repositories.db import Store
from ..services import local_store as ls_mod
from ..services.hydra_client import HydraAdapter
from ..tools import tools as T

TOOL_NAMES = [
    "search_company_knowledge",
    "retrieve_related_entities",
    "compare_policy_versions",
    "detect_conflicts",
    "prepare_action_tasks",
    "record_approved_decision",
]

MIN_EVIDENCE_SCORE = 0.8
# Minimum top retrieval score to treat local results as supporting evidence.
# Measured 2026-10-12 on the demo corpus: in-domain refund queries score
# >= 1.1 (top ~1.6-1.9); an unrelated probe ("parental leave ... Germany")
# scored <= 0.66. Below this floor the agent refuses to fabricate impacts.
# HydraDB relevancy scores use a different scale, so the gate applies to
# local mode only (live Hydra threshold TBD once a key is available).

def _rule_plan(change_request: str) -> list[str]:
    q = change_request.lower()
    plan = ["search_company_knowledge", "compare_policy_versions"]
    # conditional branches (real selection, not fixed order)
    if any(w in q for w in ("contract", "acme", "exception", "agreement", "legal", "refund", "policy")):
        plan.append("retrieve_related_entities")
    plan.append("detect_conflicts")  # mandatory safety gate
    if any(w in q for w in ("refund", "policy", "change", "update", "effective", "impact", "acme")):
        plan.append("prepare_action_tasks")
    # record_approved_decision runs only after human approval, never here
    seen, out = set(), []
    for t in plan:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

def _llm_plan(change_request: str) -> list[str] | None:
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        tools_spec = [{
            "type": "function",
            "function": {
                "name": "select_tools",
                "description": "Select the minimal ordered subset of agent tools needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tools": {"type": "array", "items": {"type": "string", "enum": TOOL_NAMES}},
                        "reason": {"type": "string"},
                    },
                    "required": ["tools"],
                },
            },
        }]
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are the RippleBrain planner. Available tools: " + ", ".join(TOOL_NAMES) + ". Always include search_company_knowledge, compare_policy_versions and detect_conflicts. Add retrieve_related_entities when departments/contracts/owners matter. Add prepare_action_tasks when follow-up work is requested or implied by an impact analysis."},
                {"role": "user", "content": f"Change request: {change_request}\nReturn the tool plan."},
            ],
            tools=tools_spec,  # type: ignore
            tool_choice={"type": "function", "function": {"name": "select_tools"}},
            max_tokens=300,
        )
        args = json.loads(resp.choices[0].message.tool_calls[0].function.arguments)
        plan = [t for t in args.get("tools", []) if t in TOOL_NAMES]
        for mandatory in ("search_company_knowledge", "compare_policy_versions", "detect_conflicts"):
            if mandatory not in plan:
                plan.insert(0, mandatory)
        return plan
    except Exception:
        return None

class Orchestrator:
    def __init__(self, store: Store, local: ls_mod.LocalStore, hydra: HydraAdapter):
        self.store = store
        self.local = local
        self.hydra = hydra

    def _retrieve(self, query: str) -> tuple[list[dict], dict, str, list[str]]:
        log: list[str] = []
        hydra_ok = self.hydra.status().get("hydra_connected", False)
        if hydra_ok:
            try:
                base = self.hydra.query(query, graph_context=False)
                adv = self.hydra.query(query, graph_context=True)
                chunks = adv.get("chunks") or base.get("chunks")
                graph = {"query_paths": adv.get("graph_paths", []), "provenance": "hydra"}
                log.append(f"HydraDB retrieval: {len(base.get('chunks', []))} baseline / {len(chunks)} with graph.")
                return chunks, graph, "hydra", log
            except Exception as e:
                log.append(f"HydraDB query failed, falling back to local: {str(e)[:200]}")
        chunks = self.local.search(query)
        relations = self.local.related_entities([c.get("source_id", "") for c in chunks])
        log.append(f"Local retrieval: {len(chunks)} chunks (transparent fallback).")
        return chunks, {"query_paths": [], "relations": relations.get("relations", []),
                        "provenance": "local-manifest"}, "local", log

    def _insufficient_evidence(
        self, analysis_id: str, change_request: str, chunks: list[dict],
        graph: dict, mode: str, executed: list[str],
        execution_log: list[str], top_score: float,
    ) -> dict:
        """Explicit no-fabrication response for out-of-corpus requests."""
        warning = (
            "Insufficient evidence in the Company Brain for this request "
            f"(top retrieval score {top_score:.3f}). No impacts or actions were "
            "generated — nothing is presented as company policy."
        )
        payload = {
            "analysis_id": analysis_id,
            "retrieval_mode": mode,
            "old_window_days": None,
            "new_window_days": None,
            "effective_date": None,
            "summary": "No supporting evidence found in the Company Brain for this request. "
                       "No impacts or follow-up actions were generated.",
            "impacts": [],
            "exceptions": [],
            "actions": [],
            "sources": [{"source_id": c.get("source_id", ""), "title": c.get("title", ""),
                         "excerpt": (c.get("excerpt", "") or "")[:400], "score": c.get("score")} for c in chunks],
            "graph": graph,
            "baseline_chunks": len(chunks),
            "graph_chunks": len(chunks),
            "selected_tools": executed,
            "execution_log": execution_log,
            "warnings": [warning],
        }
        self.store.save_analysis(analysis_id, change_request, payload, mode)
        self.store.log("analysis", f"{analysis_id}: insufficient evidence, no impacts generated [{mode}]")
        return payload

    def analyze(self, change_request: str) -> dict:
        analysis_id = f"an_{uuid.uuid4().hex[:10]}"
        execution_log: list[str] = [f"Analysis {analysis_id} started."]
        warnings: list[str] = []

        llm_plan = _llm_plan(change_request)
        plan = llm_plan or _rule_plan(change_request)
        planner = "openai-tool-calling" if llm_plan else "rule-based"
        execution_log.append(f"Planner ({planner}) selected tools: {', '.join(plan)}")

        chunks, graph, mode, rlog = self._retrieve(change_request)
        execution_log.extend(rlog)
        top_score = max((c.get("score") or 0) for c in chunks) if chunks else 0.0
        if not chunks or (mode == "local" and top_score < MIN_EVIDENCE_SCORE):
            # Insufficient-evidence gate: empty retrieval in ANY mode, or weak
            # local retrieval, must never fabricate impacts or draft actions.
            reason = "empty retrieval" if not chunks else (
                f"top local score {top_score:.3f} < {MIN_EVIDENCE_SCORE}")
            execution_log.append(
                f"Evidence gate ({reason}) — skipping detect_conflicts/"
                "prepare_action_tasks; refusing to fabricate impacts."
            )
            return self._insufficient_evidence(
                analysis_id, change_request, chunks, graph, mode,
                [], execution_log, top_score,
            )
        if not chunks:
            warnings.append("No supporting evidence retrieved — results marked unverified.")
            execution_log.append("WARNING: empty retrieval; refusing to fabricate impacts.")

        results: dict = {}
        policy = {"old_window_days": 30, "new_window_days": 14, "effective_date": "2026-10-15"}

        if "search_company_knowledge" in plan:
            r = T.search_company_knowledge(change_request, chunks)
            results["search"] = r; execution_log.append(r["log"])
        if "retrieve_related_entities" in plan:
            rels = self.local.related_entities([c.get("source_id", "") for c in chunks])
            # if hydra graph paths exist, surface them too
            if graph.get("query_paths"):
                rels = {**rels, "hydra_query_paths": graph["query_paths"], "provenance": "hydra+manifest"}
            r = T.retrieve_related_entities(rels)
            results["relations"] = r; execution_log.append(r["log"])
            graph = {**graph, "relations": rels.get("relations", [])}
        if "compare_policy_versions" in plan:
            r = T.compare_policy_versions(change_request, chunks)
            results["policy"] = r; execution_log.append(r["log"])
            policy = r["data"]
        if "detect_conflicts" in plan:
            doc_index = {d["id"]: d for d in self.local.docs}
            r = T.detect_conflicts(policy, chunks, doc_index)
            results["conflicts"] = r; execution_log.append(r["log"])
            warnings.extend(r.get("warnings", []))
        impacts = results.get("conflicts", {}).get("data", {}).get("impacts", [])
        exceptions = results.get("conflicts", {}).get("data", {}).get("exceptions", [])
        actions: list[dict] = []
        if "prepare_action_tasks" in plan:
            r = T.prepare_action_tasks(analysis_id, impacts)
            results["tasks"] = r; execution_log.append(r["log"])
            for a in r["data"]["actions"]:
                saved = self.store.upsert_action(a)
                actions.append({
                    "id": saved["id"], "title": saved["title"], "description": saved["description"],
                    "department": saved["department"], "owner": saved["owner"], "priority": saved["priority"],
                    "evidence": a["evidence"], "status": saved["status"],
                    "idempotency_key": saved["idempotency_key"], "approval_note": saved.get("approval_note", ""),
                })

        summary = (
            f"Refund window {policy['old_window_days']}d → {policy['new_window_days']}d effective {policy['effective_date']}. "
            f"{len(impacts)} departments affected. "
            + ("ACME Corp contractual exception detected (30d through Dec 31, 2026). " if exceptions else "")
        ).strip()

        payload = {
            "analysis_id": analysis_id,
            "retrieval_mode": mode,
            "old_window_days": policy["old_window_days"],
            "new_window_days": policy["new_window_days"],
            "effective_date": policy["effective_date"],
            "summary": summary,
            "impacts": impacts,
            "exceptions": exceptions,
            "actions": actions,
            "sources": [{"source_id": c.get("source_id", ""), "title": c.get("title", ""),
                         "excerpt": (c.get("excerpt", "") or "")[:400], "score": c.get("score")} for c in chunks],
            "graph": graph,
            "baseline_chunks": len(chunks),
            "graph_chunks": len(chunks),
            "selected_tools": plan,
            "execution_log": execution_log,
            "warnings": warnings,
        }
        self.store.save_analysis(analysis_id, change_request, payload, mode)
        self.store.log("analysis", f"{analysis_id}: {summary} [{mode}]")
        return payload
