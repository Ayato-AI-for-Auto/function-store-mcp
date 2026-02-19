import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp_core.core.config import DATA_DIR, TRANSPORT
from mcp_core.core.database import _check_model_version, init_db
from mcp_core.engine.logic import do_delete_impl as _do_delete_impl
from mcp_core.engine.logic import do_get_history_impl as _do_get_history_impl
from mcp_core.engine.logic import do_get_impl as _do_get_impl
from mcp_core.engine.logic import do_save_impl as _do_save_impl
from mcp_core.engine.logic import do_search_impl as _do_search_impl

# ----------------------------------------------------------------------
# Logging Setup
# ----------------------------------------------------------------------
LOG_FILE = os.path.join(DATA_DIR, "server.log")
ERROR_LOG_FILE = os.path.join(DATA_DIR, "error.log")

info_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
info_handler.setLevel(logging.INFO)

error_handler = RotatingFileHandler(
    ERROR_LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
error_handler.setLevel(logging.ERROR)

stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[stream_handler, info_handler, error_handler],
    force=True,
)
# Suppress verbose third-party logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp = FastMCP("Function Store", dependencies=["uvicorn"])

# ----------------------------------------------------------------------
# MCP Tools
# ----------------------------------------------------------------------


@mcp.tool()
def search_functions(query: str, limit: int = 5) -> List[Dict]:
    """
    Search for reusable Python functions using natural language queries and semantic similarity.
    Use this to find existing logic before writing new code to avoid "reinventing the wheel".
    
    Args:
        query: A natural language description of the functionality needed (e.g., "resize image", "calculate distance").
        limit: Max number of results (default 5).
        
    Returns:
        List of function metadata objects, including name, description, and quality score.
    """
    return _do_search_impl(query, limit)


@mcp.tool()
def list_functions(
    query: Optional[str] = None, tag: Optional[str] = None, limit: int = 100
) -> List[Dict]:
    """
    List all stored functions with optional exact-match filtering.
    Use this for browsing the collection or finding functions by specific tags.
    
    Args:
        query: Keyword to search for in name or description (case-insensitive exact match).
        tag: Specific tag to filter by (e.g., "math", "image-processing").
        limit: Max number of results (default 100).
        
    Returns:
        List of function metadata objects.
    """
    # We'll need to implement this in logic.py or just do it here for now
    # Let's add it to logic.py for consistency
    from mcp_core.engine.logic import do_list_impl

    return do_list_impl(query=query, tag=tag, limit=limit)


# Internal statistic tool (Not exposed to MCP)
def get_dashboard_stats() -> Dict:
    """Get summarized statistics for the dashboard."""
    from mcp_core.engine.logic import get_stats_impl

    return get_stats_impl()


@mcp.tool()
def save_function(
    name: str,
    code: str,
    description: str = "",
    tags: List[str] = [],
    dependencies: List[str] = [],
    test_cases: List[Dict] = [],
    skip_test: bool = False,
    description_en: Optional[str] = None,
    description_jp: Optional[str] = None,
) -> str:
    """
    Saves or updates a Python function in the persistent vector store.
    Automatically triggers AST analysis, quality checks (Ruff), and embedding generation.
    
    Args:
        name: Unique identifier for the function (e.g., "calculate_bmi").
        code: Full Python source code of the function.
        description: Primary documentation for humans and AI search.
        tags: List of categories for easy discovery.
        dependencies: External library names (pip) required by the function.
        test_cases: List of inputs/outputs to verify correctness.
        skip_test: If True, skips functional tests (useful for rapid sketching).
        
    Returns:
        Confirmation message with version number.
        
    Note:
        IMPORTANT: This system does NOT manage cross-function dependencies (e.g., Function A calling Function B stored in the same store). 
        To ensure portability, please save interdependent functions as a single, self-contained code unit (Integrated Version).
    """
    return _do_save_impl(
        name,
        code,
        description,
        tags,
        dependencies,
        test_cases,
        skip_test,
        description_en,
        description_jp,
    )


@mcp.tool()
def delete_function(name: str) -> str:
    """
    Permanently deletes a function and all its version history from the store.
    Use this only when code is obsolete or incorrect.
    
    Args:
        name: Name of the function to delete.
        
    Returns:
        Success or error message.
    """
    return _do_delete_impl(name)


@mcp.tool()
def get_function(name: str) -> str:
    """
    Retrieves the raw Python source code of a specific function.
    Use this when you want to use the function logic in your current project.
    
    Args:
        name: Name of the function to retrieve.
        
    Returns:
        Python source code as a string, or error message if not found.
    """
    return _do_get_impl(name)


@mcp.tool()
def get_function_details(name: str) -> Dict:
    """
    Retrieves the full metadata for a function, including quality metrics and test status.
    Use this to understand the reliability and origins of a code asset.
    
    Args:
        name: Name of the function.
        
    Returns:
        Detailed dictionary of metadata, including tags, call counts, and quality score.
    """
    from mcp_core.engine.logic import do_get_details_impl

    return do_get_details_impl(name)


@mcp.tool()
def get_function_history(name: str) -> List[Dict]:
    """
    Retrieves the complete version history of a function.
    Useful for tracking changes or rolling back to previous logic.
    
    Args:
        name: Name of the function.
        
    Returns:
        List of historical versions with descriptions and timestamps.
    """
    return _do_get_history_impl(name)


# Internal batch tool (Not exposed to MCP)
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
                skip_test=True,
            )
            results.append(res)

        return (
            f"Imported {len(data)} functions: "
            + " | ".join(results[:3])
            + ("..." if len(results) > 3 else "")
        )
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_triage_list(limit: int = 5) -> List[Dict]:
    """
    Identifies "broken" functions in the store that need human or AI attention.
    Prioritizes functions with failed tests or low quality scores.
    
    Args:
        limit: Max number of candidates (default 5).
        
    Returns:
        List of summaries for functions requiring maintenance.
    """
    from mcp_core.engine.triage import triage_engine

    return triage_engine.get_broken_functions(limit)


@mcp.tool()
def get_fix_advice(name: str) -> str:
    """
    Generates a detailed "Repair Manual" for a broken function using a local LLM.
    Use this when you encounter a function with a low score and want to fix it.
    
    Args:
        name: Name of the function to analyze.
        
    Returns:
        Diagnostic report including lint errors, test results, and step-by-step fix strategy.
    """
    from mcp_core.engine.triage import triage_engine

    report = triage_engine.get_diagnostic_report(name)
    if not report:
        return f"Error: Function '{name}' not found."

    # Generate advice using LLM
    advice = triage_engine.generate_repair_advice(report)

    return (
        f"--- Diagnostic Report for '{name}' ---\n"
        f"Status: {report['status']}\n"
        f"Quality Score: {report['quality_score']}\n\n"
        f"Repair Advice (Local LLM):\n{advice}\n\n"
        f"Code to Fix:\n```python\n{report['code']}\n```"
    )


def main():
    """Entry point for the mcp-core server."""
    init_db()
    _check_model_version()
    # Start FastMCP
    mcp.run(transport=TRANSPORT)


if __name__ == "__main__":
    main()
