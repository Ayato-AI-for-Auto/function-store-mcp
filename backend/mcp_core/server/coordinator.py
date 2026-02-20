import logging
import socket
import sys
import time

import httpx
from mcp_core.core.config import HOST, PORT

logger = logging.getLogger(__name__)

# Primary Master Port (different from main API port if used for GUI)
MASTER_PORT = PORT + 100  # Example: 8101 if default is 8001


class Coordinator:
    """
    Handles multi-process coordination for MCP.
    Decides if the current process should be the Master or a Proxy.
    """

    def __init__(self):
        self.master_url = f"http://{HOST}:{MASTER_PORT}"

    def is_master_running(self) -> bool:
        """Checks if a Master process is already listening on the designated port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect((HOST, MASTER_PORT))
                return True
            except (socket.timeout, ConnectionRefusedError):
                return False

    def start_master_invisible(self):
        """Starts the Master process in the background without a window."""
        logger.info("Coordinator: Starting Master process in background...")
        cmd = [sys.executable, "-m", "mcp_core.server.background_server"]

        # Use flags to hide window on Windows
        creationflags = 0
        if sys.platform == "win32":
            import subprocess

            creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

        subprocess.Popen(
            cmd,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

        # Wait a bit for it to wake up
        for _ in range(10):
            if self.is_master_running():
                logger.info("Coordinator: Master process is now running.")
                return
            time.sleep(0.5)
        logger.error("Coordinator: Failed to start Master process.")

    def proxy_request(self, tool_name: str, arguments: dict) -> dict:
        """Proxies the Tool request to the Master process."""
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.master_url}/execute",
                    json={"tool": tool_name, "arguments": arguments},
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Coordinator: Proxy request failed: {e}")
            return {
                "error": f"Proxy Error: Master process is unresponsive or returned an error: {e}"
            }


# Global Instance
coordinator = Coordinator()
