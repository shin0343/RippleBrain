from __future__ import annotations
import io
import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..models.schemas import (
    ActivityItem, AnalyzeRequest, BrainStatus, HealthResponse, SourceInfo, ApproveRequest,
)
from ..repositories.db import Store
from ..services.local_store import LocalStore
from ..services.hydra_client import HydraAdapter
from ..agents.orchestrator import Orchestrator

router = APIRouter()

def _deps() -> tuple[Store, LocalStore, HydraAdapter]:
    store = Store(settings.sqlite_path)
    local = LocalStore(settings.data_dir)
    hydra = HydraAdapter()
    return store, local, hydra

@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()

@router.get("/brain/status", response_model=BrainStatus)
def brain_status():
    store, local, hydra = _deps()
    h = hydra.status()
    n = len(local.docs)
    mode = h.get("retrieval_mode", "local")
    return BrainStatus(
        hydra_configured=h.get("hydra_configured", False),
        hydra_connected=h.get("hydra_connected", False),
        hydra_database=settings.hydra_database,
        hydra_collection=settings.hydra_collection,
        retrieval_mode=mode if mode in ("hydra", "local") else "local",
        indexed_sources=n,
        sources_completed=n,
        message=h.get("message", ""),
    )

@router.get("/brain/sources", response_model=list[SourceInfo])
def brain_sources():
    _, local, _ = _deps()
    return [SourceInfo(**{**s, "indexing_status": "local-ready"}) for s in local.sources()]

class SeedResponse(BaseModel):
    ok: bool
    mode: str
    ingested: int
    message: str

@router.post("/brain/seed", response_model=SeedResponse)
def brain_seed():
    store, local, hydra = _deps()
    if hydra.status().get("hydra_connected"):
        try:
            # Never re-ingest blindly: upsert resets server-side indexing
            # progress. If the 12 demo sources already exist, report state.
            try:
                existing = hydra.list_sources()
            except Exception:
                existing = []
            if len(existing) >= 12:
                from collections import Counter
                states = Counter(hydra.indexing_states([s["id"] for s in existing]))
                done = states.get("completed", 0)
                store.log("seed", f"Seed skipped: {len(existing)} sources already present ({done} completed)")
                if done >= 12:
                    msg = "12 demo sources already indexed — Company Brain ready."
                else:
                    msg = (f"12 demo sources present; indexing in progress ({done}/12 completed) — "
                           "retrieval works now, full graph context once complete.")
                return SeedResponse(ok=True, mode="hydra", ingested=len(existing), message=msg)
            docs = []
            company = os.path.join(settings.data_dir, "company")
            for fn in sorted(os.listdir(company)):
                if fn.endswith(".md"):
                    with open(os.path.join(company, fn), encoding="utf-8") as f:
                        md = f.read()
                    doc_id = fn.replace(".md", "")
                    title = doc_id
                    for line in md.splitlines():
                        if line.startswith("title:"):
                            title = line.split(":", 1)[1].strip().strip('"')
                    docs.append({"id": doc_id, "title": title, "markdown": md})
            graph = local.graph
            # wrap into expected graph_payload shape
            res = hydra.seed(docs, {"entities": graph.get("entities", {}), "relations": graph.get("relations", [])}, timeout_s=30)
            store.log("seed", f"HydraDB seed OK: {res['ingested']} sources (indexing={res.get('indexing')})")
            if res.get("indexing") == "pending":
                msg = (f"Ingested {res['ingested']} sources; HydraDB indexing still in progress — "
                       "retrieval works now, full graph context once indexing completes.")
            else:
                msg = "Seeded HydraDB knowledge + graph (indexing complete)."
            return SeedResponse(ok=True, mode="hydra", ingested=res["ingested"], message=msg)
        except Exception as e:
            store.log("seed_error", f"HydraDB seed failed: {e}")
            raise HTTPException(status_code=502, detail=f"HydraDB seed failed: {e}")
    store.log("seed", f"Local dataset ready: {len(local.docs)} sources (HydraDB not configured)")
    return SeedResponse(ok=True, mode="local", ingested=len(local.docs), message="HydraDB not configured — local dataset verified (transparent fallback).")

@router.post("/changes/analyze")
def analyze(req: AnalyzeRequest):
    store, local, hydra = _deps()
    orch = Orchestrator(store, local, hydra)
    try:
        return orch.analyze(req.change_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str):
    store, _, _ = _deps()
    res = store.get_analysis(analysis_id)
    if not res:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return res

@router.get("/analyses/{analysis_id}/evidence")
def get_evidence(analysis_id: str):
    store, _, _ = _deps()
    res = store.get_analysis(analysis_id)
    if not res:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"analysis_id": analysis_id, "sources": res.get("sources", []),
            "graph": res.get("graph", {}), "retrieval_mode": res.get("retrieval_mode")}

@router.get("/actions")
def list_actions(status: str | None = None):
    store, _, _ = _deps()
    return {"actions": store.list_actions(status)}

@router.post("/actions/{action_id}/approve")
def approve_action(action_id: str, req: ApproveRequest):
    store, _, hydra = _deps()
    updated = store.set_action_status(action_id, "approved", req.note)
    if not updated:
        raise HTTPException(status_code=404, detail="Action not found")
    mem_text = f"Approved: {updated['title']} [{updated['department']}] owner {updated['owner']}. Note: {req.note or '—'}"
    mem_id = store.add_memory(mem_text)
    hydra_mem: str | None = None
    if hydra.status().get("hydra_connected"):
        try:
            r = hydra.ingest_memory([mem_text])
            hydra_mem = ",".join(r.get("ids", []))
        except Exception as e:
            store.log("memory_error", f"HydraDB memory ingest failed: {e}")
    return {**updated, "local_memory_id": mem_id, "hydra_memory_ids": hydra_mem,
            "memory_status": "hydra" if hydra_mem else "local"}

@router.post("/actions/{action_id}/reject")
def reject_action(action_id: str, req: ApproveRequest):
    store, _, _ = _deps()
    updated = store.set_action_status(action_id, "rejected", req.note)
    if not updated:
        raise HTTPException(status_code=404, detail="Action not found")
    return updated

@router.get("/activity", response_model=list[ActivityItem])
def activity():
    store, _, _ = _deps()
    return store.list_activity()
