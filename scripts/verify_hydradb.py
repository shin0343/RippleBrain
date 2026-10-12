"""Verify HydraDB ingestion + retrieval. Skips gracefully without API key."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv()

def main():
    key = os.environ.get("HYDRA_DB_API_KEY", "")
    if not key:
        print("SKIP: HYDRA_DB_API_KEY not set. HydraDB verification NOT VERIFIED (transparent local mode).")
        return 0
    from app.config import settings
    from app.services.hydra_client import HydraAdapter
    from app.services.local_store import LocalStore
    local = LocalStore(settings.data_dir)
    hydra = HydraAdapter()
    st = hydra.status()
    print("status:", st)
    if not st.get("hydra_connected"):
        print("NOT VERIFIED: cannot reach HydraDB with the configured key.")
        return 2
    try:
        print("local docs:", len(local.docs))
        q = "refund policy 30 days to 14 days effective October 15 2026"
        base = hydra.query(q, graph_context=False)
        adv = hydra.query(q, graph_context=True)
        print(f"baseline chunks={len(base['chunks'])} graph chunks={len(adv['chunks'])} paths={len(adv['graph_paths'])}")
        if not base["chunks"]:
            print("NOT VERIFIED: no chunks retrieved (run scripts/seed_company.py first).")
            return 2
    except Exception as e:
        print(f"NOT VERIFIED: HydraDB query failed: {e}")
        return 2
    print("HydraDB retrieval OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
