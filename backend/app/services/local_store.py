from __future__ import annotations
import json
import math
import os
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+")

# Same untrusted-instruction patterns as tools.scan_injection. Excerpts are
# truncated, so a bait string buried at the end of a long doc would otherwise
# never reach the scanner. Surfacing the snippet (labeled, as data) keeps the
# defense-in-depth check live on real retrieval paths.
_INJECTION_RES = [
    re.compile(r"skip all .*approval", re.I),
    re.compile(r"system override", re.I),
    re.compile(r"ignore .*approv", re.I),
    re.compile(r"mark every action approved", re.I),
]

def _tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())

def _parse_frontmatter(path: str) -> tuple[dict, str]:
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    meta: dict = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            try:
                import yaml  # type: ignore
                meta = yaml.safe_load(parts[1]) or {}
            except Exception:
                meta = {}
                for line in parts[1].splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"').strip("'")
            body = parts[2]
    return meta, body.strip()

class LocalStore:
    """Transparent local retrieval used when HydraDB is unavailable.

    Always labeled as retrieval_mode='local' — never presented as HydraDB.
    Implements a small hybrid of keyword overlap + length-normalized TF scoring.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.docs: list[dict] = []
        self.graph: dict = {"entities": {}, "relations": []}
        self._load()

    def _load(self) -> None:
        company = os.path.join(self.data_dir, "company")
        if os.path.isdir(company):
            for fn in sorted(os.listdir(company)):
                if not fn.endswith(".md"):
                    continue
                meta, body = _parse_frontmatter(os.path.join(company, fn))
                doc_id = str(meta.get("id", fn.replace(".md", "")))
                self.docs.append({
                    "id": doc_id,
                    "title": str(meta.get("title", doc_id)),
                    "document_type": str(meta.get("document_type", "")),
                    "department": str(meta.get("department", "")),
                    "owner": str(meta.get("owner", "")),
                    "version": str(meta.get("version", "")),
                    "effective_from": str(meta.get("effective_from", "") or ""),
                    "effective_until": str(meta.get("effective_until", "") or ""),
                    "status": str(meta.get("status", "") or ""),
                    "source_reference": str(meta.get("source_reference", "") or ""),
                    "body": body,
                    "tokens": Counter(_tokens(f"{meta.get('title','')} {body}")),
                })
        gpath = os.path.join(self.data_dir, "relationships", "graph.json")
        if os.path.exists(gpath):
            with open(gpath, encoding="utf-8") as f:
                self.graph = json.load(f)

    def sources(self) -> list[dict]:
        return [
            {k: d[k] for k in ("id", "title", "document_type", "department", "owner", "version", "effective_from", "effective_until", "status") if k in d}
            for d in self.docs
        ]

    def search(self, query: str, top_k: int = 8) -> list[dict]:
        qt = Counter(_tokens(query))
        scored = []
        for d in self.docs:
            overlap = sum(min(qt[t], d["tokens"][t]) for t in qt if t in d["tokens"])
            if overlap == 0:
                continue
            norm = math.sqrt(sum(v * v for v in d["tokens"].values())) or 1.0
            score = overlap / math.sqrt(len(qt) or 1) / math.log10(100 + norm)
            # boosts for policy/contract relevance on refund queries
            if "refund" in qt and d["id"] in ("refund_policy_v2", "refund_policy_v1", "acme_agreement", "support_faq"):
                score *= 1.25
            scored.append((score, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, d in scored[:top_k]:
            body = d["body"]
            excerpt = body[:420].replace("\n", " ")
            for rx in _INJECTION_RES:
                m = rx.search(body)
                if m:
                    start = max(0, m.start() - 60)
                    snippet = body[start:m.end() + 60].replace("\n", " ")
                    excerpt += f" [QUARANTINED embedded instruction-like text, ignored as data: \"...{snippet}...\"]"
                    break
            out.append({
                "source_id": d["id"],
                "title": d["title"],
                "excerpt": excerpt,
                "score": round(float(score), 4),
            })
        return out

    def related_entities(self, source_ids: list[str]) -> dict:
        """Return manifest-backed relations touching the given sources (local graph)."""
        names = {d["id"]: d["title"] for d in self.docs}
        rels = self.graph.get("relations", [])
        ents = self.graph.get("entities", {})
        # keep relations mentioning policy/contract/doc keywords
        keywords = set(source_ids) | {"policy_v2", "policy_v1", "doc_faq", "doc_acme", "doc_std", "doc_sop", "doc_sales"}
        picked = [r for r in rels if r.get("source") in keywords or r.get("target") in keywords]
        return {"entities": ents, "relations": picked or rels, "provenance": "local-manifest"}
