"""Parser unit tests for HydraAdapter.query (no API key needed; stubbed client)."""
import os, sys
from types import SimpleNamespace
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.hydra_client import HydraAdapter

def _triplet(src, pred, tgt):
    return SimpleNamespace(source={"name": src},
                           relation={"canonical_predicate": pred},
                           target={"name": tgt})

def _stub_client(chunks, paths, chunk_rels):
    resp = SimpleNamespace(data=SimpleNamespace(
        chunks=chunks,
        graph_context=SimpleNamespace(query_paths=paths, chunk_relations=chunk_rels),
    ))
    return SimpleNamespace(query=lambda **kw: resp)

def test_query_parses_paths_and_chunk_relations():
    chunks = [SimpleNamespace(source_id="01_x", source_title="Doc X",
                              chunk_content="---\nid: refund_policy_v2\ntitle: \"Refund Policy v2\"\n---\nbody",
                              relevancy_score=0.9)]
    paths = [SimpleNamespace(triplets=[_triplet("a", "IMPACTS", "b")], relevancy_score=0.5)]
    crels = [SimpleNamespace(triplets=[_triplet("c", "OVERRIDES", "d")],
                             group_id="p_0", combined_context="ctx", relevancy_score=0.1)]
    adapter = HydraAdapter.__new__(HydraAdapter)
    adapter._client = _stub_client(chunks, paths, crels)
    out = HydraAdapter.query(adapter, "q", graph_context=True)
    assert out["chunks"][0]["source_id"] == "refund_policy_v2"
    assert out["graph_paths"][0]["triplets"] == [
        {"source": "a", "predicate": "IMPACTS", "target": "b"}]
    assert out["chunk_relations"][0]["triplets"] == [
        {"source": "c", "predicate": "OVERRIDES", "target": "d"}]
    assert out["chunk_relations"][0]["group_id"] == "p_0"

def test_query_handles_missing_graph():
    chunks = [SimpleNamespace(source_id="s", source_title="T",
                              chunk_content="text", relevancy_score=0.1)]
    resp = SimpleNamespace(data=SimpleNamespace(chunks=chunks, graph_context=None))
    adapter = HydraAdapter.__new__(HydraAdapter)
    adapter._client = SimpleNamespace(query=lambda **kw: resp)
    out = HydraAdapter.query(adapter, "q", graph_context=False)
    assert out["graph_paths"] == [] and out["chunk_relations"] == []
