"""Seed Company Brain: ingests local dataset into HydraDB if configured, else verifies local dataset."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv()
from app.config import settings
from app.services.local_store import LocalStore
from app.services.hydra_client import HydraAdapter

def main():
    local = LocalStore(settings.data_dir)
    print(f"Local dataset: {len(local.docs)} docs, {len(local.graph.get('relations', []))} relations")
    hydra = HydraAdapter()
    st = hydra.status()
    print("HydraDB:", st)
    if not st.get("hydra_connected"):
        print("Local mode: dataset verified, no HydraDB ingestion (set HYDRA_DB_API_KEY to enable).")
        return 0
    docs = []
    import glob
    for path in sorted(glob.glob(os.path.join(settings.data_dir, "company", "*.md"))):
        with open(path, encoding="utf-8") as f:
            md = f.read()
        docs.append({"id": os.path.basename(path).replace(".md", ""), "title": os.path.basename(path), "markdown": md})
    try:
        res = hydra.seed(docs, local.graph)
    except Exception as e:
        print(f"SEED FAILED (NOT VERIFIED): {e}")
        return 1
    print("Seeded:", res)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
