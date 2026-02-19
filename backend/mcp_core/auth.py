import secrets

import duckdb
from mcp_core.core.config import API_KEYS_DB_PATH


def generate_api_key(user_id: str) -> str:
    """Generates a new API key and stores it in the database."""
    key = f"fsk_{secrets.token_urlsafe(24)}"

    conn = duckdb.connect(str(API_KEYS_DB_PATH))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS api_keys (key TEXT PRIMARY KEY, user_id TEXT)"
        )
        conn.execute("INSERT OR REPLACE INTO api_keys VALUES (?, ?)", [key, user_id])
    finally:
        conn.close()

    return key


def verify_api_key(key: str):
    """Verifies an API key against the database."""
    conn = duckdb.connect(str(API_KEYS_DB_PATH), read_only=True)
    try:
        # Table must already exist. If not, select will fail.
        res = conn.execute(
            "SELECT user_id FROM api_keys WHERE key = ?", [key]
        ).fetchone()
        if res:
            return True, res[0]
        return False, None
    except Exception:
        # If table doesn't exist yet, it's not a valid key
        return False, None
    finally:
        conn.close()
