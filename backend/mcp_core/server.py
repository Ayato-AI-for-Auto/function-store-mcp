from typing import Dict, List

from mcp.server.fastmcp import FastMCP
from mcp_core.core.config import TRANSPORT
from mcp_core.core.database import _check_model_version, init_db
from mcp_core.engine.logic import (
    do_delete_impl,
    do_get_details_impl,
    do_get_impl,
    do_inject_impl,
    do_list_impl,
    do_save_impl,
    do_search_impl,
    do_smart_get_impl,
    do_triage_list_impl,
)
from mcp_core.infra.ipc_manager import ipc_manager

# Initialize FastMCP
mcp = FastMCP("function-store", dependencies=["duckdb", "fastembed"])


def _master_executor(tool_name: str, arguments: dict):
    """Execution logic for the Master process."""
    try:
        if tool_name == "save_function":
            return do_save_impl(**arguments)
        elif tool_name == "search_functions":
            return do_search_impl(**arguments)
        elif tool_name == "get_function_details":
            return do_get_details_impl(**arguments)
        elif tool_name == "delete_function":
            return do_delete_impl(**arguments)
        elif tool_name == "list_functions":
            return do_list_impl(**arguments)
        elif tool_name == "get_function":
            return do_get_impl(**arguments)
        elif tool_name == "inject_local_package":
            return do_inject_impl(**arguments)
        elif tool_name == "smart_search_and_get":
            return do_smart_get_impl(**arguments)
        elif tool_name == "get_triage_list":
            return do_triage_list_impl(**arguments)
        else:
            return f"Error: Unknown tool {tool_name}"
    except Exception as e:
        return f"Error: {str(e)}"


def _execute_proxied(tool_name: str, **kwargs):
    """Logic to decide if to execute locally or proxy via IPC."""
    if ipc_manager.role == "MASTER":
        return _master_executor(tool_name, kwargs)
    else:
        resp = ipc_manager.proxy_call(tool_name, kwargs)
        if isinstance(resp, dict) and "error" in resp:
            return resp["error"]
        return resp.get("result")


# ----------------------------------------------------------------------
# MCP Tools
# ----------------------------------------------------------------------


@mcp.tool()
def search_functions(query: str, limit: int = 5) -> List[Dict]:
    """
    [EXPLORATION TOOL] Catalog search for reusable functions.
    Use this to 'browse' or 'explore' what logic exists before deciding to use it.
    For automated integration, use 'smart_search_and_get' instead.
    """
    return _execute_proxied("search_functions", query=query, limit=limit)


@mcp.tool()
def save_function(
    name: str,
    code: str,
    description: str = "",
    tags: List[str] = [],
    dependencies: List[str] = [],
    test_cases: List[Dict] = [],
    skip_test: bool = False,
) -> str:
    """
    Saves or updates a Python function in the persistent vector store.
    """
    return _execute_proxied(
        "save_function",
        asset_name=name,  # Note: logic.py uses asset_name
        code=code,
        description=description,
        tags=tags,
        dependencies=dependencies,
        test_cases=test_cases,
        skip_test=skip_test,
    )


@mcp.tool()
def delete_function(name: str) -> str:
    """
    Permanently deletes a function from the store.
    """
    return _execute_proxied("delete_function", asset_name=name)


@mcp.tool()
def get_function(name: str, integrate_dependencies: bool = False) -> str:
    """
    [SPECIFICATION/DEBUG TOOL] Retrieves the raw source code of a specific function.
    Use this to 'read' the logic, understand its implementation, or for debugging.
    Set integrate_dependencies=True to get a self-contained bundle for inspection.
    """
    return _execute_proxied(
        "get_function", asset_name=name, integrate_dependencies=integrate_dependencies
    )


@mcp.tool()
def get_function_details(name: str) -> Dict:
    """
    Retrieves the full metadata for a function.
    """
    return _execute_proxied("get_function_details", name=name)


@mcp.tool()
def inject_local_package(function_names: List[str], target_dir: str = "./") -> str:
    """
    [PROFESSIONAL TARGETING TOOL] Physically exports specified functions to 'local_pkg/'.
    Use this when you already know EXACTLY which functions you want to sync.
    For discovery-based integration, use 'smart_search_and_get'.
    """
    return _execute_proxied(
        "inject_local_package", function_names=function_names, target_dir=target_dir
    )


@mcp.tool()
def smart_search_and_get(query: str, target_dir: str = "./") -> Dict:
    """
    [PRIMARY AI PROTOCOL] Intent-based Search -> Selection -> Injection.
    Input your natural language request (e.g., 'JSON parsing logic'),
    and this tool will optimally find, resolve, and physically deploy the
    best-matching code into your 'local_pkg/' directory.
    RECOMMENDED: Use this as the default tool for fulfilling user requests.
    """
    return _execute_proxied("smart_search_and_get", query=query, target_dir=target_dir)


@mcp.tool()
def get_triage_list(limit: int = 5) -> List[Dict]:
    """
    Identifies "broken" functions in the store that need attention.
    """
    return _execute_proxied("get_triage_list", limit=limit)


def main():
    """Entry point for the mcp-core server."""
    role, _ = ipc_manager.determine_role()
    if role == "MASTER":
        init_db()
        _check_model_version()
        ipc_manager.start_master_loop(_master_executor)

    mcp.run(transport=TRANSPORT)


if __name__ == "__main__":
    main()
