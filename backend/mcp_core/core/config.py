import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = Path(os.getenv("FS_DATA_DIR", BASE_DIR / "data"))
SETTINGS_PATH = DATA_DIR / "settings.json"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load settings from data/settings.json (UI-first design, no .env required)
_settings = {}
if SETTINGS_PATH.exists():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            _settings = json.load(f)
    except Exception:
        pass


def get_setting(key: str, default=None):
    """Gets a setting from UI-saved settings.json, then falls back to env var, then default."""
    return _settings.get(key) or os.getenv(key, default)


# Derived Paths
ENVS_DIR = Path(os.getenv("FS_ENVS_DIR", BASE_DIR / ".mcp_envs"))
ENVS_DIR.mkdir(parents=True, exist_ok=True)

# Database Paths
DB_PATH = DATA_DIR / get_setting("FS_DB_NAME", "functions.duckdb")
API_KEYS_DB_PATH = DATA_DIR / get_setting("FS_API_KEYS_DB_NAME", "api_keys.duckdb")

# Server Config
HOST = get_setting("FS_HOST", "0.0.0.0")
PORT = int(get_setting("FS_PORT", "8001"))
TRANSPORT = get_setting("FS_TRANSPORT", "stdio")

# Local AI Config
EMBEDDING_MODEL_ID = get_setting(
    "FS_EMBEDDING_MODEL_ID", "jinaai/jina-embeddings-v2-base-code"
)
LLM_MODEL_ID = get_setting("FS_LLM_MODEL_ID", "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF")
GGUF_FILENAME = get_setting("FS_GGUF_FILENAME", "qwen2.5-coder-3b-instruct-q4_k_m.gguf")

# Models Cache Directory
CACHE_DIR = DATA_DIR / "models"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Quality Gate Config (Local AI)
# We use the same LLM for both description and quality scoring if needed
QUALITY_GATE_MODEL = get_setting("FS_QUALITY_GATE_MODEL", LLM_MODEL_ID)
DESCRIPTION_MODEL = get_setting("FS_DESCRIPTION_MODEL", LLM_MODEL_ID)

# Sync Config (GitHub Serverless DB)
SYNC_ENABLED = get_setting("FS_SYNC_ENABLED", "True").lower() == "true"
SYNC_REPO_URL = get_setting(
    "FS_SYNC_REPO_URL", "https://github.com/Ayato-AI-for-Auto/function-store-hub.git"
)
SYNC_LOCAL_DIR = DATA_DIR / "hub_cache"
SYNC_LOCAL_DIR.mkdir(parents=True, exist_ok=True)

# Execution Runtime Config
# Options: "auto" (local venv), "docker" (containerized), "cloud" (managed)
EXECUTION_MODE = get_setting("FS_EXECUTION_MODE", "auto")
