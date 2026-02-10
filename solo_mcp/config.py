import os
import json
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent.parent
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

# Embedding Config
MODEL_NAME = get_setting("FS_MODEL_NAME", "models/gemini-embedding-001")
GOOGLE_API_KEY = get_setting("GOOGLE_API_KEY")

# Quality Gate Config
QUALITY_GATE_MODEL = get_setting("FS_QUALITY_GATE_MODEL", "gemma-3-27b-it")

# Execution Runtime Config
# Options: "process" (default, local venv), "docker" (containerized)
EXECUTION_MODE = get_setting("FS_EXECUTION_MODE", "auto")

# HuggingFace Token (for TranslateGemma)
HF_TOKEN = get_setting("HF_TOKEN")
