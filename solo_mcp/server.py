import os
import sys
import json
import logging
from typing import List, Dict, Optional

from mcp.server.fastmcp import FastMCP
from logging.handlers import RotatingFileHandler

from solo_mcp.config import (
    DATA_DIR, TRANSPORT
)
from solo_mcp.database import get_db_connection, init_db, _check_model_version
from solo_mcp.workers import (
    translation_worker, sync_agent, dashboard_exporter
)
from solo_mcp.logic import (
    do_save_impl as _do_save_impl,
    do_search_impl as _do_search_impl,
    do_get_impl as _do_get_impl,
    do_get_history_impl as _do_get_history_impl
)

# ----------------------------------------------------------------------
# Logging Setup
# ----------------------------------------------------------------------
LOG_FILE = os.path.join(DATA_DIR, "server.log")
ERROR_LOG_FILE = os.path.join(DATA_DIR, "error.log")

info_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
info_handler.setLevel(logging.INFO)

error_handler = RotatingFileHandler(ERROR_LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
error_handler.setLevel(logging.ERROR)

stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[stream_handler, info_handler, error_handler],
    force=True
)
logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp = FastMCP("Function Store", dependencies=["uvicorn"])

# ----------------------------------------------------------------------
# MCP Tools
# ----------------------------------------------------------------------

@mcp.tool()
def search_functions(query: str, limit: int = 5) -> List[Dict]:
    """Search for reusable Python functions using natural language query."""
    return _do_search_impl(query, limit)

@mcp.tool()
def save_function(name: str, code: str, description: str = "", tags: List[str] = [], dependencies: List[str] = [], test_cases: List[Dict] = [], skip_test: bool = False, description_en: Optional[str] = None, description_jp: Optional[str] = None) -> str:
    """Saves a Python function to the persistent vector store."""
    return _do_save_impl(name, code, description, tags, dependencies, test_cases, skip_test, description_en, description_jp)

@mcp.tool()
def delete_function(name: str) -> str:
    """Delete a function from the store by name."""
    conn = get_db_connection()
    try:
        # DuckDB doesn't support ON DELETE CASCADE, so we must clean up manually
        row = conn.execute("SELECT id FROM functions WHERE name = ?", (name,)).fetchone()
        if row:
            fid = row[0]
            conn.execute("DELETE FROM embeddings WHERE function_id = ?", (fid,))
            conn.execute("DELETE FROM function_versions WHERE function_id = ?", (fid,))
            conn.execute("DELETE FROM functions WHERE id = ?", (fid,))
            conn.commit()
            return f"SUCCESS: Function '{name}' and its history deleted."
        return f"Error: Function '{name}' not found."
    finally:
        conn.close()

@mcp.tool()
def get_function(name: str) -> str:
    """Retrieve the full source code of a specific function."""
    return _do_get_impl(name)

@mcp.tool()
def get_function_history(name: str) -> List[Dict]:
    """Retrieve the version history of a function."""
    return _do_get_history_impl(name)

@mcp.tool()
def import_function_pack(json_data: str) -> str:
    """Import a list of functions from a JSON string."""
    try:
        data = json.loads(json_data)
        if not isinstance(data, list):
            return "Error: JSON must be a list of function objects."
        
        results = []
        for i, func_def in enumerate(data):
            # Map keys and call internal save
            res = _do_save_impl(
                asset_name=func_def.get("name"),
                code=func_def.get("code"),
                description=func_def.get("description", ""),
                tags=func_def.get("tags", []),
                dependencies=func_def.get("dependencies", []),
                test_cases=func_def.get("test_cases", []),
                skip_test=True
            )
            results.append(res)
        
        return f"Imported {len(data)} functions: " + " | ".join(results[:3]) + ("..." if len(results) > 3 else "")
    except Exception as e:
        return f"Error: {str(e)}"

# --- Main Server Execution ---
if __name__ == "__main__":
    init_db()
    _check_model_version()
    
    # Initialize background agents
    translation_worker.start()
    sync_agent.start()
    dashboard_exporter.start()
    
    # Start FastMCP
    mcp.run(transport=TRANSPORT)
