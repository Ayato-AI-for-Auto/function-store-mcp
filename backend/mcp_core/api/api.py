# Function Store REST API

from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp_core.auth import verify_api_key
from mcp_core.engine.logic import (
    do_get_impl as _do_get_impl,
)
from mcp_core.engine.logic import (
    do_save_impl as _do_save_impl,
)
from mcp_core.engine.logic import (
    do_search_impl as _do_search_impl,
)
from pydantic import BaseModel

app = FastAPI(
    title="Function Store API",
    description="REST API for AI-powered code asset management",
    version="0.1.0",
)

# CORS for Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user(x_api_key: Optional[str] = Header(None)):
    """
    Verify API key from header.
    TODO : For Public Web UI, we might need a read-only public key or bypass.
    Current logic enforces strict auth, which is good for the "Private Vault" phase.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    is_valid, user_id = verify_api_key(x_api_key)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return user_id


# --- Models ---
class FunctionCreate(BaseModel):
    asset_name: str
    code: str
    description: Optional[str] = ""
    dependencies: Optional[List[str]] = []
    test_cases: Optional[List[Dict[str, Any]]] = []
    tags: Optional[List[str]] = []
    auto_generate_tests: Optional[bool] = False


class SearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 5


# --- Endpoints ---
@app.get("/")
def root():
    return {"message": "Function Store API", "version": "0.1.0", "status": "running"}


@app.get("/health")
def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy"}


@app.post("/functions", response_model=Dict)
async def create_function(
    func: FunctionCreate, user_id: str = Depends(get_current_user)
):
    """
    Save a new function to the store.
    """
    try:
        # Strict positional call to avoid keyword conflict with FastAPI/MCP
        result = _do_save_impl(
            func.asset_name,
            func.code,
            func.description or "",
            func.tags or [],
            func.dependencies or [],
            func.test_cases or [],
            not (func.auto_generate_tests or False),
        )
        return {"message": result, "name": func.asset_name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/functions/{function_name}")
async def get_function_by_name(
    function_name: str, user_id: str = Depends(get_current_user)
):
    """Get a specific function by name."""
    try:
        # Positional call to bypass keyword injection
        result = _do_get_impl(function_name)
        if result.startswith("Function '") and "not found" in result:
            raise HTTPException(status_code=404, detail=result)
        return {"code": result}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/functions/search")
async def search(query: SearchQuery, user_id: str = Depends(get_current_user)):
    """
    Semantic search for functions using vector similarity.
    """
    try:
        results = _do_search_impl(query.query, query.limit or 5)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Startup ---
if __name__ == "__main__":
    import uvicorn

    print("Starting Function Store REST API on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
