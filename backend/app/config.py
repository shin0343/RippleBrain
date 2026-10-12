import os
from dataclasses import dataclass

def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)

@dataclass
class Settings:
    hydra_api_key: str = ""
    hydra_database: str = "ripplebrain_demo"
    hydra_collection: str = "northstar_knowledge"
    hydra_memory_collection: str = "approvals_memory"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    data_dir: str = ""
    sqlite_path: str = ""
    backend_port: int = 8000

def load_settings() -> Settings:
    from dotenv import load_dotenv
    load_dotenv()
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # backend/ -> repo root
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    s = Settings()
    s.hydra_api_key = os.environ.get("HYDRA_DB_API_KEY", "")
    s.hydra_database = os.environ.get("HYDRA_DATABASE", "ripplebrain_demo")
    s.hydra_collection = os.environ.get("HYDRA_COLLECTION", "northstar_knowledge")
    s.hydra_memory_collection = os.environ.get("HYDRA_MEMORY_COLLECTION", "approvals_memory")
    s.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    s.openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    s.data_dir = os.environ.get("DATA_DIR", os.path.join(root, "data"))
    s.sqlite_path = os.environ.get("SQLITE_PATH", os.path.join(root, "data", "ripplebrain.db"))
    return s

settings = load_settings()
