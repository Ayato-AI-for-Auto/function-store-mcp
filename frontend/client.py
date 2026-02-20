import json
import logging
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SoloClient:
    """
    Client for the Function Store MCP server using STDIO transport.
    Ensures that ONLY the server process touches the DuckDB database.
    """

    def __init__(self, python_exe: str, server_script: str):
        if getattr(sys, "frozen", False):
            # In frozen state, the current executable is the server
            self.python_exe = sys.executable
            self.server_script = "--server"
            self.is_frozen = True
        else:
            self.python_exe = python_exe
            self.server_script = server_script
            self.is_frozen = False

        self.process = None
        self.msg_id = 0
        self.pending_requests = {}
        self.read_thread = None
        self._is_ready = False

    def start(self):
        """Starts the MCP server as a subprocess."""
        cmd = [self.python_exe, self.server_script]

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        # Wait for initialize or just assume ready after a bit
        time.sleep(1)
        self._is_ready = True
        logger.info(f"MCP Server started (Frozen: {self.is_frozen}).")

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process = None

    def _read_loop(self):
        """Continuously read JSON-RPC responses from the server's stdout."""
        if not self.process:
            return

        for line in iter(self.process.stdout.readline, ""):
            if not line:
                break
            try:
                msg = json.loads(line)
                if "id" in msg:
                    req_id = msg["id"]
                    if req_id in self.pending_requests:
                        self.pending_requests[req_id]["response"] = msg
                        self.pending_requests[req_id]["event"].set()
            except Exception as e:
                logger.error(f"Error reading from MCP server: {e} | Line: {line}")

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool via JSON-RPC."""
        if not self.process or not self._is_ready:
            # Try to auto-start if not running
            self.start()

        self.msg_id += 1
        req_id = self.msg_id
        event = threading.Event()
        self.pending_requests[req_id] = {"event": event, "response": None}

        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        try:
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
        except OSError as e:
            logger.error(f"Failed to write to MCP server: {e}")
            return {"error": str(e)}

        # Wait for response with timeout
        if not event.wait(timeout=30.0):
            del self.pending_requests[req_id]
            raise TimeoutError(f"Tool call '{tool_name}' timed out.")

        response = self.pending_requests[req_id]["response"]
        del self.pending_requests[req_id]

        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")

        # FastMCP returns a List[TextContent | ImageContent | EmbeddedResource]
        # We assume the tool returns a string or list/dict in the 'text' field
        content = response.get("result", {}).get("content", [])
        if content:
            # Most tools in this project return JSON-string or List/Dict in text field
            text_val = content[0].get("text", "")
            try:
                return json.loads(text_val)
            except Exception:
                return text_val
        return None

    def list_functions(
        self, query: Optional[str] = None, tag: Optional[str] = None
    ) -> List[Dict]:
        return self._call_tool("list_functions", {"query": query, "tag": tag}) or []

    def get_stats(self) -> Dict:
        return self._call_tool("get_dashboard_stats", {}) or {}

    def save_function(self, **kwargs) -> str:
        return (
            self._call_tool("save_function", kwargs) or "Error: No response from server"
        )

    def delete_function(self, name: str) -> str:
        return (
            self._call_tool("delete_function", {"name": name})
            or "Error: No response from server"
        )

    def get_function_details(self, name: str) -> Optional[Dict]:
        res = self._call_tool("get_function_details", {"name": name})
        if res and isinstance(res, dict) and "error" in res:
            return None
        return res
