"""HydraDB adapter. Real SDK calls only; on any failure returns local mode.

Never misrepresents local results as HydraDB results. All responses carry
retrieval_mode and provenance explicitly.
"""
from __future__ import annotations
import io
import json
import re
import time
import os
from typing import Any

from ..config import settings

_FRONT_ID = re.compile(r"^id:\s*(\S+)", re.M)
_FRONT_TITLE = re.compile(r"^title:\s*\"?([^\"]+)\"?", re.M)


def _triplet(t: Any) -> dict:
    def name(o: Any) -> str:
        if o is None:
            return "unknown"
        if isinstance(o, dict):
            return str(o.get("name", "?"))
        return str(getattr(o, "name", "?"))

    def pred(o: Any) -> str:
        if isinstance(o, dict):
            return str(o.get("canonical_predicate", "RELATED_TO"))
        return str(getattr(o, "canonical_predicate", "RELATED_TO"))

    return {"source": name(getattr(t, "source", None)),
            "predicate": pred(getattr(t, "relation", None)),
            "target": name(getattr(t, "target", None))}


class HydraAdapter:
    def __init__(self):
        self.configured = bool(settings.hydra_api_key)
        self._client = None
        self._last_error: str = ""
        if self.configured:
            try:
                from hydra_db import HydraDB  # lazy import; SDK optional at runtime
                self._client = HydraDB(token=settings.hydra_api_key)
            except Exception as e:  # pragma: no cover
                self._last_error = f"SDK init failed: {e}"
                self._client = None

    @property
    def last_error(self) -> str:
        return self._last_error

    def status(self, timeout_s: float = 8.0) -> dict:
        if not self._client:
            return {
                "hydra_configured": self.configured,
                "hydra_connected": False,
                "retrieval_mode": "local",
                "message": self._last_error or "HYDRA_DB_API_KEY not set — running in transparent local mode.",
            }
        try:
            st = self._client.databases.status(database=settings.hydra_database)
            ready = bool(getattr(getattr(st, "data", None), "infra", None) and st.data.infra.ready_for_ingestion)
            return {
                "hydra_configured": True,
                "hydra_connected": True,
                "retrieval_mode": "hydra",
                "infra_ready": ready,
                "message": "Connected to HydraDB.",
            }
        except Exception as e:
            # A 404 here usually means the database was never created, not
            # that the service is down. Confirm reachability with a cheap
            # list call so callers can distinguish "reachable, needs seed"
            # from "unreachable".
            try:
                self._client.databases.list()
                return {
                    "hydra_configured": True,
                    "hydra_connected": True,
                    "retrieval_mode": "hydra",
                    "infra_ready": False,
                    "database_exists": False,
                    "message": f"Reachable; database {settings.hydra_database!r} not provisioned yet — run seed.",
                }
            except Exception as e2:
                self._last_error = str(e2)[:300]
                return {
                    "hydra_configured": True,
                    "hydra_connected": False,
                    "retrieval_mode": "local",
                    "message": f"HydraDB unreachable: {self._last_error}",
                }

    # ---- ingestion ----
    def seed(self, docs: list[dict], graph: dict, timeout_s: int = 240) -> dict:
        """Create DB, ingest knowledge docs + graph_payload, poll indexing. Raises on failure."""
        if not self._client:
            raise RuntimeError("HydraDB not configured")
        from hydra_db.errors import ConflictError
        client = self._client
        try:
            client.databases.create(database=settings.hydra_database)
        except ConflictError:
            pass
        # wait for provisioning (bounded)
        start = time.time()
        while time.time() - start < 90:
            st = client.databases.status(database=settings.hydra_database)
            if st.data.infra.ready_for_ingestion:
                break
            time.sleep(4)
        else:
            raise TimeoutError("HydraDB database provisioning timed out")

        def text_file(filename: str, content: str):
            return (filename, io.BytesIO(content.encode("utf-8")), "text/plain")

        source_ids: list[str] = []
        # ingest markdown docs one call (SDK accepts single file per call reliably; batch metadata)
        for d in docs:
            meta = [{"id": d["id"],
                     "additional_metadata": {"title": d["title"],
                                             "document_type": d.get("document_type", ""),
                                             "department": d.get("department", ""),
                                             "owner": d.get("owner", "")}}]
            kwargs: dict[str, Any] = {
                "database": settings.hydra_database,
                "collection": settings.hydra_collection,
                "type": "knowledge",
                "documents": text_file(f'{d["id"]}.md', d["markdown"]),
                "document_metadata": json.dumps(meta),
                "upsert": "true",
            }
            if d["id"] == "workflow_manifest" or d["id"].endswith("workflow_manifest"):
                # graph_payload key must equal this document's metadata id.
                kwargs["graph_payload"] = json.dumps({d["id"]: graph})
            res = client.context.ingest(**kwargs)
            source_ids.extend([r.id for r in res.data.results])
        try:
            self._wait_completed(source_ids, settings.hydra_collection, timeout_s)
        except TimeoutError:
            # Ingestion accepted; indexing still running server-side.
            # Report honestly instead of failing the whole seed.
            return {"ingested": len(source_ids), "source_ids": source_ids,
                    "indexing": "pending"}
        return {"ingested": len(source_ids), "source_ids": source_ids,
                "indexing": "completed"}

    def _wait_completed(self, ids: list[str], collection: str, timeout_s: int) -> None:
        # Guide-aligned: `graph_creation` is already searchable (graph may be
        # partial); `completed` is fully indexed and graphed.
        client = self._client
        assert client is not None
        start = time.time()
        while time.time() - start < timeout_s:
            st = client.context.status(database=settings.hydra_database, collection=collection, ids=ids)
            states = [s.indexing_status for s in st.data.statuses]
            if all(s in ("completed", "graph_creation") for s in states):
                return
            if any(s in ("errored", "failed") for s in states):
                # A scope miss (wrong database/collection) also reports
                # errored with FILE_NOT_FOUND — name it, don't guess.
                codes = {getattr(s, "error_code", "") or "" for s in st.data.statuses}
                if "FILE_NOT_FOUND" in codes:
                    raise RuntimeError(
                        "No such id in this scope: check database/collection match ingestion")
                raise RuntimeError(f"HydraDB indexing failed: {states}")
            time.sleep(5)
        raise TimeoutError("HydraDB indexing did not complete within timeout")

    def list_sources(self) -> list[dict]:
        """Lightweight inventory of the knowledge collection. Raises on failure."""
        if not self._client:
            raise RuntimeError("HydraDB not configured")
        lst = self._client.context.list(
            database=settings.hydra_database, collection=settings.hydra_collection)
        return [{"id": s.id, "title": getattr(s, "title", "") or s.id}
                for s in (lst.data.sources or [])]

    def indexing_states(self, ids: list[str]) -> list[str]:
        """Indexing states for the given source ids. Raises on failure."""
        if not self._client:
            raise RuntimeError("HydraDB not configured")
        st = self._client.context.status(
            database=settings.hydra_database, collection=settings.hydra_collection, ids=ids)
        return [s.indexing_status for s in st.data.statuses]

    # ---- query ----
    def query(self, query: str, graph_context: bool, max_results: int = 10) -> dict:
        """Returns normalized {chunks, graph_paths, provenance}. Raises on failure."""
        if not self._client:
            raise RuntimeError("HydraDB not configured")
        res = self._client.query(
            database=settings.hydra_database,
            collection=settings.hydra_collection,
            query=query,
            type="knowledge",
            query_by="hybrid",
            mode="thinking" if graph_context else "fast",
            max_results=max_results,
            graph_context=graph_context,
        )
        chunks = []
        for c in (res.data.chunks or []):
            raw_id = getattr(c, "source_id", None) or getattr(c, "id", "") or ""
            content = getattr(c, "chunk_content", None) or ""
            # Normalize to canonical doc ids: our markdown carries
            # `id:` / `title:` frontmatter, while Hydra source ids are
            # filename-based. Keeps evidence mapping consistent across modes.
            head = content[:800]
            mid = _FRONT_ID.search(head)
            mtitle = _FRONT_TITLE.search(head)
            chunks.append({
                "source_id": mid.group(1).strip() if mid else raw_id,
                "title": mtitle.group(1).strip().strip('"') if mtitle else (
                    getattr(c, "source_title", None) or raw_id or ""),
                "excerpt": content[:500],
                "score": getattr(c, "relevancy_score", None),
            })
        paths: list[dict] = []
        chunk_rels: list[dict] = []
        g = getattr(res.data, "graph_context", None)
        if g:
            for p in (getattr(g, "query_paths", None) or []):
                triplets = [_triplet(t) for t in (getattr(p, "triplets", None) or [])]
                paths.append({"triplets": triplets,
                              "relevancy": getattr(p, "relevancy_score", None)})
            for cr in (getattr(g, "chunk_relations", None) or []):
                triplets = [_triplet(t) for t in (getattr(cr, "triplets", None) or [])]
                chunk_rels.append({"triplets": triplets,
                                   "group_id": getattr(cr, "group_id", None),
                                   "combined_context": (getattr(cr, "combined_context", None) or "")[:300],
                                   "relevancy": getattr(cr, "relevancy_score", None)})
        return {"chunks": chunks, "graph_paths": paths,
                "chunk_relations": chunk_rels, "provenance": "hydra"}

    def ingest_memory(self, texts: list[str]) -> dict:
        if not self._client:
            raise RuntimeError("HydraDB not configured")
        payload = [{"text": t, "infer": False} for t in texts]
        res = self._client.context.ingest(
            database=settings.hydra_database,
            collection=settings.hydra_memory_collection,
            type="memory",
            memories=json.dumps(payload),
            upsert="true",
        )
        return {"ids": [r.id for r in res.data.results]}
