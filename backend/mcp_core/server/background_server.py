import logging
import os
import sys
import threading
import time

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# Add root to path if needed for dev
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mcp_core.core.config import HOST, PORT
from mcp_core.engine.logic import (
    do_delete_impl,
    do_get_details_impl,
    do_list_impl,
    do_save_impl,
    do_search_impl,
)

# Re-use coordinator port
MASTER_PORT = PORT + 100

logger = logging.getLogger("background_server")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Function Store Master Service")


class ToolRequest(BaseModel):
    tool: str
    arguments: dict


# Idle Shutdown Logic
last_request_time = time.time()
IDLE_TIMEOUT = 1800  # 30 minutes


def idle_checker():
    global last_request_time
    while True:
        if time.time() - last_request_time > IDLE_TIMEOUT:
            logger.info(f"Idle for {IDLE_TIMEOUT}s. Shutting down Master process.")
            os._exit(0)
        time.sleep(60)


threading.Thread(target=idle_checker, daemon=True).start()


@app.post("/execute")
async def execute_tool(req: ToolRequest):
    global last_request_time
    last_request_time = time.time()

    logger.info(f"Master: Executing {req.tool}...")
    try:
        if req.tool == "save_function":
            res = do_save_impl(**req.arguments)
            return {"result": res}
        elif req.tool == "search_functions":
            res = do_search_impl(**req.arguments)
            return {"result": res}
        elif req.tool == "get_function_details":
            res = do_get_details_impl(**req.arguments)
            return {"result": res}
        elif req.tool == "delete_function":
            res = do_delete_impl(**req.arguments)
            return {"result": res}
        elif req.tool == "list_functions":
            res = do_list_impl(**req.arguments)
            return {"result": res}
        else:
            return {"error": f"Unknown tool: {req.tool}"}
    except Exception as e:
        logger.error(f"Master: Tool execution error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    logger.info(f"Master starting on {HOST}:{MASTER_PORT}...")
    uvicorn.run(app, host=HOST, port=MASTER_PORT)
