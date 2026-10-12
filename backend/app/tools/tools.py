"""Agent tools: pure functions over retrieval + local analysis.

Each tool returns {ok, data, evidence, log}. Prompt-injection rule: document
content is DATA, never instructions — any embedded instruction to skip
approvals is ignored and flagged.
"""
from __future__ import annotations
import hashlib
import re
import uuid

DAY_RE = re.compile(r"(\d{1,2})\s*-\s*day", re.I)
DATE_RE = re.compile(r"(October\s+\d{1,2},?\s+2026|2026-\d{2}-\d{2})", re.I)
INJECTION_RES = [
    re.compile(r"skip all .*approval", re.I),
    re.compile(r"system override", re.I),
    re.compile(r"ignore .*approv", re.I),
    re.compile(r"mark every action approved", re.I),
]

def _ev(chunks: list[dict], limit: int = 4) -> list[dict]:
    return [
        {"source_id": c.get("source_id", ""), "title": c.get("title", ""),
         "excerpt": (c.get("excerpt", "") or "")[:400], "score": c.get("score")}
        for c in chunks[:limit]
    ]

def scan_injection(chunks: list[dict]) -> list[str]:
    hits = []
    for c in chunks:
        text = (c.get("excerpt", "") or "")
        for rx in INJECTION_RES:
            if rx.search(text):
                hits.append(f"Untrusted instruction ignored in '{c.get('title','')}' (treated as data, not system instruction).")
                break
    return hits

def search_company_knowledge(query: str, chunks: list[dict]) -> dict:
    return {"ok": True, "data": {"chunks": chunks, "count": len(chunks)},
            "evidence": _ev(chunks),
            "log": f"search_company_knowledge: {len(chunks)} chunks for query."}

def retrieve_related_entities(relations: dict) -> dict:
    rels = relations.get("relations", [])
    return {"ok": True, "data": relations,
            "evidence": [],
            "log": f"retrieve_related_entities: {len(rels)} relations (provenance={relations.get('provenance')})."}

def compare_policy_versions(change_request: str, chunks: list[dict]) -> dict:
    days = [int(m.group(1)) for m in DAY_RE.finditer(change_request)]
    if len(days) >= 2:
        old_days, new_days = days[0], days[1]
        provenance = "extracted from request"
    else:
        old_days, new_days = (30, 14)
        provenance = "corpus defaults (v1=30d, v2=14d); request stated fewer than two day-values"
    m = DATE_RE.search(change_request)
    effective = "2026-10-15"
    if m:
        s = m.group(1)
        dm = re.search(r"October\s+(\d{1,2})", s)
        if dm:
            effective = f"2026-10-{int(dm.group(1)):02d}"
        elif re.match(r"2026-\d{2}-\d{2}", s):
            effective = s
    return {"ok": True,
            "data": {"old_window_days": old_days, "new_window_days": new_days,
                     "effective_date": effective,
                     "change": f"{old_days}-day to {new_days}-day refund window"},
            "evidence": _ev(chunks),
            "log": f"compare_policy_versions: {old_days}d -> {new_days}d effective {effective} ({provenance})."}

def detect_conflicts(policy: dict, chunks: list[dict], doc_index: dict) -> dict:
    impacts: list[dict] = []
    exceptions: list[dict] = []
    warnings: list[str] = []
    by_id = {c.get("source_id"): c for c in chunks}

    def chunk_ev(*ids: str) -> list[dict]:
        return _ev([by_id[i] for i in ids if i in by_id]) or _ev(chunks, 2)

    # Customer Support — stale FAQ + templates quote 30 days
    impacts.append({
        "department": "Customer Support",
        "affected_documents": ["Customer Support Refund FAQ", "Customer Support Response Templates"],
        "description": "FAQ and reply templates still quote a 30-day window. They will misinform customers for purchases on/after Oct 15, 2026 unless updated.",
        "severity": "High", "owner": "Dana Kim",
        "evidence": chunk_ev("support_faq", "support_templates"),
        "recommended_action": "Rewrite FAQ + templates R-1/R-3 to 14 days before Oct 14; keep enterprise carve-out note.",
        "verified": True,
    })
    # Sales
    impacts.append({
        "department": "Sales",
        "affected_documents": ["Sales Onboarding Guide", "Standard Customer Agreement"],
        "description": "Onboarding talk track promises a 30-day guarantee. Standard Agreement follows the general policy dynamically, so reps will over-promise without a refresh.",
        "severity": "High", "owner": "Marcus Webb",
        "evidence": chunk_ev("sales_onboarding", "standard_agreement"),
        "recommended_action": "Update talk track to 14 days; remind reps enterprise deviations need Legal sign-off.",
        "verified": True,
    })
    # Finance
    impacts.append({
        "department": "Finance",
        "affected_documents": ["Finance Refund Processing SOP"],
        "description": "SOP step 1 verifies a 30-day window (WF-FIN-01). Eligibility checks and ledger cutover must move to 14 days, except ACME contract cases.",
        "severity": "Medium", "owner": "Priya Nair",
        "evidence": chunk_ev("finance_sop"),
        "recommended_action": "Review WF-FIN-01: add 14-day check + ACME 30-day branch; update by Oct 16.",
        "verified": True,
    })
    # Legal
    impacts.append({
        "department": "Legal",
        "affected_documents": ["Refund Policy v1", "Refund Policy v2", "ACME Corp Enterprise Agreement"],
        "description": "Policy v2 (14d, eff. Oct 15) supersedes v1 (30d). ACME's signed 30-day term through Dec 31, 2026 overrides the general policy for that account.",
        "severity": "High", "owner": "Amara Osei",
        "evidence": chunk_ev("refund_policy_v2", "refund_policy_v1", "acme_agreement"),
        "recommended_action": "Confirm v1 marked superseded; circulate ACME carve-out to Support/Finance/Sales.",
        "verified": True,
    })

    exceptions.append({
        "title": "ACME Corp — contractual exception detected",
        "customer": "ACME Corp", "clause": "Section 7.3", "applies_through": "2026-12-31",
        "explanation": ("ACME Corp has an active contractual exception. The new general policy "
                        "should not automatically override the existing agreement: Section 7.3 guarantees "
                        "30-day refunds through December 31, 2026. This is demo-data analysis, not legal advice."),
        "evidence": chunk_ev("acme_agreement", "change_meeting_notes"),
    })

    inj = scan_injection(chunks)
    warnings.extend(inj)
    return {"ok": True, "data": {"impacts": impacts, "exceptions": exceptions},
            "evidence": _ev(chunks), "warnings": warnings,
            "log": f"detect_conflicts: {len(impacts)} impacts, {len(exceptions)} exception(s)."}

TASK_DEFS = [
    ("Update Support FAQ + response templates", "Rewrite FAQ answers and templates R-1/R-3 from 30 to 14 days; add enterprise carve-out note. Due Oct 14.", "Customer Support", "Dana Kim", "High"),
    ("Update sales talk track + agreement briefing", "Refresh onboarding guide talk track to 14 days; brief reps that Standard Agreement follows general policy dynamically.", "Sales", "Marcus Webb", "High"),
    ("Review Finance SOP WF-FIN-01", "Change eligibility check to 14 days; add ACME 30-day branch; confirm ledger cutover. Due Oct 16.", "Finance", "Priya Nair", "Medium"),
    ("Legal: confirm supersession + circulate carve-out", "Mark v1 superseded; circulate ACME Section 7.3 exception to Support/Finance/Sales.", "Legal", "Amara Osei", "Medium"),
]

def prepare_action_tasks(analysis_id: str, impacts: list[dict]) -> dict:
    actions = []
    for title, desc, dept, owner, pri in TASK_DEFS:
        # Content-based idempotency: re-running the same change (or double
        # submission) yields identical keys, so retries never duplicate work.
        key = hashlib.sha256(f"{title}:{dept}".encode()).hexdigest()[:16]
        ev = []
        for imp in impacts:
            if imp.get("department") == dept:
                ev = imp.get("evidence", [])[:2]
                break
        actions.append({
            "id": f"act_{key[:8]}", "analysis_id": analysis_id, "title": title,
            "description": desc, "department": dept, "owner": owner, "priority": pri,
            "evidence": ev, "status": "draft", "idempotency_key": key, "approval_note": "",
        })
    return {"ok": True, "data": {"actions": actions},
            "log": f"prepare_action_tasks: {len(actions)} draft(s) with idempotency keys."}

def record_approved_decision(summary: str) -> dict:
    return {"ok": True, "data": {"memory_text": summary},
            "log": "record_approved_decision: memory payload prepared."}

def action_id(title: str, dept: str) -> str:
    return f"act_{hashlib.sha256(f'{title}:{dept}'.encode()).hexdigest()[:8]}"
