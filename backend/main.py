import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("solo-mcp-executor")

app = FastAPI(title="Solo-MCP Cloud Executor")


class ExecutionRequest(BaseModel):
    code: str
    test_cases: List[Dict]


class ExecutionResponse(BaseModel):
    status: str
    error: Optional[str] = None
    results: Optional[List[Dict]] = None


def _create_runner_script(code: str, test_cases: List[Dict]) -> str:
    """Creates a standalone runner script to execute code and test cases."""
    return f"""
import json
import traceback

def run():
    namespace = {{}}
    try:
        exec({repr(code)}, namespace)
    except Exception:
        return {{"status": "error", "error": "Compilation/Setup Error:\\n" + traceback.format_exc()}}

    candidates = [v for k, v in namespace.items() if callable(v) and not k.startswith('_')]
    if not candidates:
        return {{"status": "error", "error": "No function found in code."}}
    func = candidates[-1]

    test_cases = {json.dumps(test_cases)}
    errors = []
    for i, tc in enumerate(test_cases):
        try:
            res = func(**tc.get('input', {{}}))
            if res != tc.get('expected'):
                errors.append(f"Test {{i+1}}: Expected {{tc.get('expected')}}, got {{res}}")
        except Exception:
            errors.append(f"Test {{i+1}}: Runtime Error - " + traceback.format_exc())

    if errors:
        return {{"status": "error", "error": "; ".join(errors)}}
    return {{"status": "success"}}

if __name__ == "__main__":
    print(json.dumps(run()))
"""


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def verify_pro_key(api_key: str):
    """Verify API Key against Supabase user_subscriptions."""
    # Note: In production, use postgrest-py or httpx to call Supabase
    # This is a template for the actual implementation
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_service_role:
        logger.warning(
            "Supabase config missing. Falling back to local/mock verification."
        )
        return api_key == "PRO-MOCK-KEY-123"

    # Mock call structure:
    # url = f"{supabase_url}/rest/v1/user_subscriptions?api_key_hash=eq.{hash_key(api_key)}&select=plan_tier,usage_count_daily,usage_limit_daily"
    # headers = {"apikey": supabase_service_role, "Authorization": f"Bearer {supabase_service_role}"}
    return True  # Placeholder for verified status


@app.post("/execute", response_model=ExecutionResponse)
async def execute(request: ExecutionRequest, x_api_key: Optional[str] = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")

    is_valid = await verify_pro_key(x_api_key)
    if not is_valid:
        raise HTTPException(
            status_code=403, detail="Invalid API Key or Pro Subscription Required"
        )

    logger.info(
        f"Executing code (len: {len(request.code)}) with {len(request.test_cases)} test cases."
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        runner_code = _create_runner_script(request.code, request.test_cases)
        runner_path = temp_path / "runner.py"
        runner_path.write_text(runner_code, encoding="utf-8")

        try:
            result = subprocess.run(
                [sys.executable, str(runner_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Execution Error: {result.stderr}")
                return ExecutionResponse(
                    status="error", error=f"Runtime Error: {result.stderr}"
                )

            try:
                output = json.loads(result.stdout.strip().splitlines()[-1])
                return ExecutionResponse(**output)
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"JSON Parse Error: {result.stdout}")
                return ExecutionResponse(
                    status="error", error=f"Internal Parser Error: {str(e)}"
                )

        except subprocess.TimeoutExpired:
            return ExecutionResponse(status="error", error="Execution Timed Out (30s)")
        except Exception as e:
            logger.exception("Unexpected exception during execution")
            return ExecutionResponse(status="error", error=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
