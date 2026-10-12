from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ripplebrain-backend"

class BrainStatus(BaseModel):
    hydra_configured: bool = False
    hydra_connected: bool = False
    hydra_database: str = ""
    hydra_collection: str = ""
    retrieval_mode: Literal["hydra", "local"] = "local"
    indexed_sources: int = 0
    sources_completed: int = 0
    message: str = ""

class SourceInfo(BaseModel):
    id: str
    title: str
    document_type: str = ""
    department: str = ""
    owner: str = ""
    version: str = ""
    effective_from: str = ""
    effective_until: str = ""
    status: str = ""
    indexing_status: str = "local-ready"

class AnalyzeRequest(BaseModel):
    change_request: str = Field(min_length=10, max_length=4000)
    compare_graph: bool = True

class EvidenceItem(BaseModel):
    source_id: str
    title: str
    excerpt: str
    score: float | None = None

class ImpactItem(BaseModel):
    department: str
    affected_documents: list[str] = []
    description: str
    severity: Literal["High", "Medium", "Low"] = "Medium"
    owner: str = ""
    evidence: list[EvidenceItem] = []
    recommended_action: str = ""
    verified: bool = True

class ExceptionItem(BaseModel):
    title: str
    customer: str = ""
    clause: str = ""
    applies_through: str = ""
    explanation: str
    evidence: list[EvidenceItem] = []

class ActionTask(BaseModel):
    id: str
    title: str
    description: str
    department: str
    owner: str = ""
    priority: Literal["High", "Medium", "Low"] = "Medium"
    evidence: list[EvidenceItem] = []
    status: Literal["draft", "approved", "rejected"] = "draft"
    idempotency_key: str = ""
    approval_note: str = ""

class AnalyzeResponse(BaseModel):
    analysis_id: str
    retrieval_mode: str
    old_window_days: int | None = None
    new_window_days: int | None = None
    effective_date: str | None = None
    summary: str
    impacts: list[ImpactItem]
    exceptions: list[ExceptionItem]
    actions: list[ActionTask]
    sources: list[EvidenceItem]
    graph: dict[str, Any] = {}
    baseline_chunks: int = 0
    graph_chunks: int = 0
    selected_tools: list[str] = []
    execution_log: list[str] = []
    warnings: list[str] = []

class ApproveRequest(BaseModel):
    note: str = Field(default="", max_length=1000)

class ActivityItem(BaseModel):
    id: int
    kind: str
    message: str
    created_at: str
