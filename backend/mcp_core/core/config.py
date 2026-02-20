import json
import os
import sys
from pathlib import Path


# Base Paths
def get_base_dir():
    """Returns the base directory of the application."""
    if getattr(sys, "frozen", False):
        # Running as a bundled .exe
        return Path(sys.executable).parent
    # Running in development
    return Path(__file__).parent.parent.parent


BASE_DIR = get_base_dir()

# Data persistence strategy:
# - Development: Use local 'data' folder
# - Frozen: Use %APPDATA%/FunctionStore to avoid data loss during app updates
if getattr(sys, "frozen", False):
    appdata = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    DATA_DIR = appdata / "FunctionStore"
else:
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


# Database Paths
DB_PATH = DATA_DIR / get_setting("FS_DB_NAME", "functions.duckdb")
API_KEYS_DB_PATH = DATA_DIR / get_setting("FS_API_KEYS_DB_NAME", "api_keys.duckdb")

# Server Config
HOST = get_setting("FS_HOST", "0.0.0.0")
PORT = int(get_setting("FS_PORT", "8001"))
TRANSPORT = get_setting("FS_TRANSPORT", "stdio")

# AI Strategy Config
# FS_MODEL_TYPE: "local" (FastEmbed) or "gemini" (Google)
MODEL_TYPE = get_setting("FS_MODEL_TYPE", "local")

EMBEDDING_MODEL_ID = get_setting(
    "FS_EMBEDDING_MODEL_ID",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
)

GEMINI_API_KEY = get_setting("FS_GEMINI_API_KEY", "")


# Models Cache Directory
CACHE_DIR = DATA_DIR / "models"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


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
